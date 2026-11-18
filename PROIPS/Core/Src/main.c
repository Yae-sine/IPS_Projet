#include "main.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* ============================================================
   Brochage STM32 (Nucleo-F411RE) <-> carte électronique
   (cf. Projet/broches.md)
     PWM          D7  = PA8   TIM1_CH1        -> LMD18200 PWM
     DIR          D6  = PB10  sortie          -> LMD18200 DIRECTION
     BRAKE        D5  = PB4   sortie          -> LMD18200 BRAKE
     Codeur A     D12 = PA6   EXTI6 (2 fronts)
     Codeur B     D13 = PA5   EXTI5 (2 fronts)   /!\ partagé avec LED LD2
     Codeur I     D11 = PA7   entrée
     Courant shunt A0 = PA0   ADC1_IN0
     CSEN driver  A1  = PA1   ADC1_IN1        <- LMD18200 Current Sense
     Flag therm.  D8  = PA9   entrée pull-up  <- LMD18200 Thermal Flag (actif bas)
   ============================================================ */

/* --- Broches du moteur --- */
#define MOTOR_DIR_PIN     GPIO_PIN_10
#define MOTOR_DIR_GPIO    GPIOB

#define MOTOR_BRAKE_PIN   GPIO_PIN_4
#define MOTOR_BRAKE_GPIO  GPIOB

/* --- Broches de l’encodeur ---
   A (PA6) et B (PA5) ne sont pas sur un même timer : aucun timer du
   F411 n'a CH1/CH2 sur PA5+PA6, donc le mode encodeur matériel est
   impossible. Décodage quadrature x4 logiciel par EXTI (EXTI9_5). */
#define ENC_GPIO          GPIOA
#define ENC_A_PIN         GPIO_PIN_6
#define ENC_B_PIN         GPIO_PIN_5
#define ENC_I_PIN         GPIO_PIN_7
#define ENC_I_GPIO        GPIOA

/* --- Mesures analogiques --- */
#define ADC_SHUNT_CHANNEL ADC_CHANNEL_0   // PA0 (A0) : ampli du shunt
#define ADC_CSEN_CHANNEL  ADC_CHANNEL_1   // PA1 (A1) : CSEN du LMD18200

/* --- Flag thermique du LMD18200 (collecteur ouvert, actif bas) --- */
#define THERM_FLAG_PIN    GPIO_PIN_9
#define THERM_FLAG_GPIO   GPIOA

/* --- Paramètres du codeur et du motoreducteur --- */
#define ENCODER_PPR       500
/* HEDS-5540 : 500 lignes, quadrature → 4 fronts par ligne = 2000 counts/tr */
#define COUNTS_PER_REV    (ENCODER_PPR * 4)

#define GEAR_RATIO        15.88f   // rapport de réduction

/* --- Variables globales --- */
TIM_HandleTypeDef htim1;
UART_HandleTypeDef huart2;
ADC_HandleTypeDef hadc1;

/* --- Décodage quadrature logiciel --- */
volatile int32_t encCount = 0;        // position codeur (coups, x4)
volatile uint8_t encPrevState = 0;    // état précédent (A<<1)|B
/* index = (ancien_etat << 2) | nouvel_etat ; transition invalide -> 0 */
static const int8_t QDEC_TABLE[16] = {
   0, -1, +1,  0,
  +1,  0,  0, -1,
  -1,  0,  0, +1,
   0, +1, -1,  0
};

/* --- Paramètres du correcteur PI (à ajuster) --- */
float Kp = 1.0f;     // Gain proportionnel (optimisé pour tracking)
float Ki = 0.25f;     // Gain intégral (optimisé pour tracking)
float err = 0.0f;    // erreur actuelle
float ui  = 0.0f;    // partie intégrale
float up  = 0.0f;    // partie proportionnelle
float control = 0.0f; // commande PI
volatile float setSpeed = 0.0f; // consigne de vitesse en RPM de sortie réducteur
volatile float savedSpeed = 0.0f; // sauvegarde de la consigne avant freinage
float targetSpeed = 0.0f;  // Consigne cible (reçue par UART)
float currentSpeed = 0.0f; // Consigne actuelle (avec rampe)

/* --- Variables pour réception UART --- */
volatile uint8_t uartRxBuffer[20];
volatile uint8_t uartRxIndex = 0;
volatile uint8_t uartRxByte;
volatile uint8_t newSpeedReceived = 0;
volatile char lastReceivedBuffer[20] = "";  // Pour debug
volatile uint8_t motorDirection = 0;  // 0 = Forward (CW), 1 = Reverse (CCW)

/* --- Prototypes --- */
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM1_Init(void);
static void Encoder_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_ADC1_Init(void);
static uint32_t ADC_ReadChannel(uint32_t channel);
void Motor_Forward(void);
void Motor_Reverse(void);
void Motor_Brake(void);
void Motor_Release(void);
void SetDutyCycle(float percent);
void Error_Handler(void);

/* ============================================================
   Fonction principale
   ============================================================ */
int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();
  MX_USART2_UART_Init();
  MX_TIM1_Init();
  MX_ADC1_Init();

  /* PWM moteur */
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
  __HAL_TIM_MOE_ENABLE(&htim1);

  /* On démarre avec duty = 0 %, ce sera le PI qui pilotera */
  SetDutyCycle(0.0f);

  /* On choisit un sens de rotation par défaut */
  Motor_Forward();

  /* Démarrage encodeur (EXTI sur A/B) */
  Encoder_Init();

  /* Démarrer la réception UART par interruption */
  HAL_UART_Receive_IT(&huart2, (uint8_t*)&uartRxByte, 1);

  /* Variables pour la vitesse */
  int32_t  lastPos  = encCount;
  uint32_t lastTime = HAL_GetTick();
  float    rpmMotorFilt = 0.0f;   // filtrage vitesse arbre moteur

  char msg[200];

  while (1)
  {
    /* Position instantanée du codeur (lecture 32 bits atomique) */
    int32_t pos = encCount;

    /* Lecture du signal Index I (0 ou 1) */
    uint8_t I = HAL_GPIO_ReadPin(ENC_I_GPIO, ENC_I_PIN);
    (void)I;

    /* Flag thermique LMD18200 : 0 = surchauffe (>145 °C) */
    uint8_t overTemp = (HAL_GPIO_ReadPin(THERM_FLAG_GPIO, THERM_FLAG_PIN) == GPIO_PIN_RESET);

    /* Courant shunt sur PA0 (A0) */
    uint32_t adcValue = ADC_ReadChannel(ADC_SHUNT_CHANNEL);

    /* Sortie Current Sense du driver sur PA1 (A1), en volts */
    uint32_t adcCsen = ADC_ReadChannel(ADC_CSEN_CHANNEL);
    float vCsen = (adcCsen * 3.3f) / 4095.0f;
    int vcs_i   = (int)vCsen;
    int vcs_dec = (int)((vCsen - vcs_i) * 100.0f);

    /* Tension (avec petit offset de 0.2 V) */
    float voltage = (adcValue * 3.3f) / 4095.0f - 0.2f;
    if (voltage < 0.0f) voltage = 0.0f;   // évite valeur négative

    int v_i   = (int)voltage;
    int v_dec = (int)((voltage - v_i) * 100.0f);
    if (v_dec < 0) v_dec = -v_dec;

    /* Courant (selon ton montage shunt & ampli) */
    float current = (voltage / 0.91f - 1.0f) / (0.05f * 67.7f);
    int   c_i   = (int)current;
    int   c_dec = (int)((current - c_i) * 100.0f);
    if (c_dec < 0) c_dec = -c_dec;

    /* --- Calcul RPM toutes les 200 ms --- */
    uint32_t now = HAL_GetTick();
    const uint32_t SAMPLE_PERIOD_MS = 200;

    if (now - lastTime >= SAMPLE_PERIOD_MS)
    {
      uint32_t deltaT_ms = (now - lastTime);   // sauvegarde avant maj
      lastTime = now;

      /* Différence de position (compteur 32 bits : pas d'overflow à gérer) */
      int32_t diff = pos - lastPos;
      lastPos = pos;

      float dt = deltaT_ms / 1000.0f;   // en secondes

      /* Vitesse moteur (arbre moteur, avant réducteur) en tr/min */
      float revs_motor = (float)diff / (float)COUNTS_PER_REV;
      float rpm_motor  = revs_motor * (60.0f / dt);

      /* Filtrage (moyenne exponentielle) sur la vitesse moteur */
      rpmMotorFilt = 0.7f * rpmMotorFilt + 0.3f * rpm_motor;

      /* Vitesse de sortie réducteur */
      float rpm_output = rpmMotorFilt / GEAR_RATIO;

      /* ========== CORRECTEUR PI SUR LA VITESSE DE SORTIE ========== */

      /* Variable duty déclarée ici pour être accessible partout */
      float duty = 0.0f;

      /* ========== RAMPE DE CONSIGNE (SLEW RATE) ========== */
      /* Transition progressive vers la consigne cible pour éviter les spikes */
      targetSpeed = setSpeed;  // Consigne reçue par UART
      float maxChange = 60.0f; // Changement max par itération (60 RPM/200ms = 300 RPM/s)
      float speedError = targetSpeed - currentSpeed;
      
      if (speedError > maxChange) {
        currentSpeed += maxChange;
      } else if (speedError < -maxChange) {
        currentSpeed -= maxChange;
      } else {
        currentSpeed = targetSpeed;
      }

      /* Le régulateur PI fonctionne toujours - c'est currentSpeed qui change */
      /* vitesse mesurée (sortie réducteur) */
      /* IMPORTANT: Inverser le signe si le moteur est en marche arrière */
      float speed = rpm_output;
      if (motorDirection == 1)  // Reverse (CCW)
      {
        speed = -speed;  // Inverser la mesure pour correspondre au sens physique
      }

      /* erreur = consigne - mesure */
      err = currentSpeed - speed;

        /* ========== FEEDFORWARD : Estimation du duty nécessaire ========== */
        /* Modèle du moteur : duty ≈ k × vitesse (calibré expérimentalement) */
        float feedforward = currentSpeed * 0.47f;  // À ajuster selon tests

        /* partie proportionnelle */
        up = Kp * err;

        /* partie intégrale inspirée de ton code : ui = ui + Kp * Ki * err */
        ui += Kp * Ki * err;
        
        /* Limiter l'intégrale pour éviter un windup excessif (cohérent avec duty max) */
        if (ui > 60.0f) ui = 60.0f;
        if (ui < -60.0f) ui = -60.0f;

        /* commande totale avec feedforward */
        control = feedforward + up + ui;

        /* Commande → duty cycle (0–100 %) */
        duty = control;

        /* Saturation préventive + anti-windup */
        if (duty > 100.0f)
        {
          duty = 100.0f;
          // Anti-windup : arrêter l'accumulation de l'intégrale
          if (err > 0) {
            ui -= Kp * Ki * err;  // Réduire ui si on sature vers le haut
          }
        }
        else if (duty < 0.0f)
        {
          duty = 0.0f;
          // Anti-windup : arrêter l'accumulation de l'intégrale
          if (err < 0) {
            ui -= Kp * Ki * err;  // Réduire ui si on sature vers le bas
          }
        }

        /* Application du duty cycle */
        SetDutyCycle(duty);

      /* ============================================================
         Affichage UART (info vitesse, direction, tension, courant)
         ============================================================ */

      /* Détermination du sens selon la vitesse moteur filtrée */
      const char *direction;
      if (rpmMotorFilt > 1.0f)
        direction = "CW";   // sens positif
      else if (rpmMotorFilt < -1.0f)
        direction = "CCW";  // sens négatif
      else
        direction = "STOP";

      /* On affiche la vitesse de sortie réducteur */
      float rpmDisp = (rpm_output >= 0.0f) ? rpm_output : -rpm_output;
      int   rpm_i   = (int)rpmDisp;
      int   rpm_dec = (int)((rpmDisp - rpm_i) * 100.0f);
      if (rpm_dec < 0) rpm_dec = -rpm_dec;

      snprintf(msg, sizeof(msg),
               "Pos=%ld  Dir=%s  RPMout=%d.%02d  Cons=%d->%d  Err=%.1f  UI=%.1f  Duty=%d%%  I=%d.%02dA  Vcs=%d.%02dV  Temp=%s\r\n",
               (long)pos, direction, rpm_i, rpm_dec,
               (int)currentSpeed, (int)setSpeed,
               err, ui,
               (int)duty, c_i, c_dec,
               vcs_i, vcs_dec, overTemp ? "HOT" : "OK");

      HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), 100);  // Timeout de 100ms au lieu de HAL_MAX_DELAY
      
      // Afficher un message spécial si une nouvelle consigne a été reçue
      if (newSpeedReceived)
      {
        char consigneMsg[80];
        snprintf(consigneMsg, sizeof(consigneMsg), ">>> RX:'%s' -> CONSIGNE = %d RPM <<<\r\n", 
                 lastReceivedBuffer, (int)setSpeed);
        HAL_UART_Transmit(&huart2, (uint8_t *)consigneMsg, strlen(consigneMsg), 100);
        newSpeedReceived = 0;
      }
    }

    HAL_Delay(10);
  }
}

/* ============================================================
   Configuration de l'horloge système (84 MHz pour STM32F411)
   ============================================================ */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM       = 8;
  RCC_OscInitStruct.PLL.PLLN       = 336;
  RCC_OscInitStruct.PLL.PLLP       = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ       = 7;

  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    Error_Handler();

  RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                     RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    Error_Handler();
}

/* ============================================================
   PWM sur TIM1 (PA8)
   ============================================================ */
static void MX_TIM1_Init(void)
{
  TIM_OC_InitTypeDef              sConfigOC = {0};
  TIM_MasterConfigTypeDef         sMasterConfig = {0};
  TIM_BreakDeadTimeConfigTypeDef  sBreakDeadTimeConfig = {0};

  __HAL_RCC_TIM1_CLK_ENABLE();

  htim1.Instance               = TIM1;
  htim1.Init.Prescaler         = 0;
  htim1.Init.CounterMode       = TIM_COUNTERMODE_UP;
  htim1.Init.Period            = 3359;   // 25 kHz pour 84 MHz
  htim1.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  HAL_TIM_PWM_Init(&htim1);

  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
  HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig);

  sConfigOC.OCMode       = TIM_OCMODE_PWM1;
  sConfigOC.Pulse        = htim1.Init.Period / 2;
  sConfigOC.OCPolarity   = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode   = TIM_OCFAST_DISABLE;
  HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1);

  sBreakDeadTimeConfig.OffStateRunMode  = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel        = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime         = 0;
  sBreakDeadTimeConfig.BreakState       = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity    = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.AutomaticOutput  = TIM_AUTOMATICOUTPUT_DISABLE;
  HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig);

  HAL_TIM_MspPostInit(&htim1);
}

/* ============================================================
   Codeur : décodage quadrature x4 par interruptions EXTI
   A = PA6 (EXTI6), B = PA5 (EXTI5) -> même vecteur EXTI9_5
   ============================================================ */
static inline uint8_t Encoder_ReadState(void)
{
  uint32_t idr = ENC_GPIO->IDR;
  return (uint8_t)(((idr & ENC_A_PIN) ? 2u : 0u) | ((idr & ENC_B_PIN) ? 1u : 0u));
}

static void Encoder_Init(void)
{
  encPrevState = Encoder_ReadState();
  encCount = 0;
  __HAL_GPIO_EXTI_CLEAR_IT(ENC_A_PIN | ENC_B_PIN);
  /* Priorité max : un front manqué = coups perdus (jusqu'à ~120 k fronts/s) */
  HAL_NVIC_SetPriority(EXTI9_5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
}

void EXTI9_5_IRQHandler(void)
{
  /* Acquitter d'abord, puis lire l'état : un front arrivant pendant
     l'ISR relancera l'interruption */
  EXTI->PR = (ENC_A_PIN | ENC_B_PIN);
  uint8_t s = Encoder_ReadState();
  encCount += QDEC_TABLE[(encPrevState << 2) | s];
  encPrevState = s;
}

/* ============================================================
   ADC1 : PA0 (IN0, shunt) et PA1 (IN1, CSEN)
   ============================================================ */
static uint32_t ADC_ReadChannel(uint32_t channel)
{
  ADC_ChannelConfTypeDef sConfig = {0};
  sConfig.Channel      = channel;
  sConfig.Rank         = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_480CYCLES;  // réduit le bruit de découpage PWM
  HAL_ADC_ConfigChannel(&hadc1, &sConfig);

  HAL_ADC_Start(&hadc1);
  HAL_ADC_PollForConversion(&hadc1, 10);
  uint32_t value = HAL_ADC_GetValue(&hadc1);
  HAL_ADC_Stop(&hadc1);
  return value;
}

static void MX_ADC1_Init(void)
{
  __HAL_RCC_ADC1_CLK_ENABLE();
  ADC_ChannelConfTypeDef sConfig = {0};

  hadc1.Instance                    = ADC1;
  hadc1.Init.ClockPrescaler         = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution             = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode           = DISABLE;
  hadc1.Init.ContinuousConvMode     = DISABLE;
  hadc1.Init.DiscontinuousConvMode  = DISABLE;
  hadc1.Init.ExternalTrigConv       = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign              = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion        = 1;
  HAL_ADC_Init(&hadc1);

  sConfig.Channel      = ADC_SHUNT_CHANNEL;
  sConfig.Rank         = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_480CYCLES;  // Augmenté pour réduire le bruit ADC
  HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}

/* ============================================================
   UART2
   ============================================================ */
static void MX_USART2_UART_Init(void)
{
  __HAL_RCC_USART2_CLK_ENABLE();

  huart2.Instance        = USART2;
  huart2.Init.BaudRate   = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits   = UART_STOPBITS_1;
  huart2.Init.Parity     = UART_PARITY_NONE;
  huart2.Init.Mode       = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl  = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  HAL_UART_Init(&huart2);
  
  /* Activer l'interruption USART2 (sous le codeur, prioritaire) */
  HAL_NVIC_SetPriority(USART2_IRQn, 1, 0);
  HAL_NVIC_EnableIRQ(USART2_IRQn);
}

/* ============================================================
   GPIO
   ============================================================ */
static void MX_GPIO_Init(void)
{
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* PWM : PA8 (TIM1_CH1) */
  GPIO_InitStruct.Pin       = GPIO_PIN_8;
  GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull      = GPIO_NOPULL;
  GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct.Alternate = GPIO_AF1_TIM1;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /* Codeur A (PA6) et B (PA5) : interruption sur les 2 fronts */
  GPIO_InitStruct.Pin       = ENC_A_PIN | ENC_B_PIN;
  GPIO_InitStruct.Mode      = GPIO_MODE_IT_RISING_FALLING;
  GPIO_InitStruct.Pull      = GPIO_PULLUP;
  GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct.Alternate = 0;
  HAL_GPIO_Init(ENC_GPIO, &GPIO_InitStruct);

  /* Index I : PA7 */
  GPIO_InitStruct.Pin   = ENC_I_PIN;
  GPIO_InitStruct.Mode  = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull  = GPIO_PULLUP;
  HAL_GPIO_Init(ENC_I_GPIO, &GPIO_InitStruct);

  /* Flag thermique LMD18200 : PA9 (collecteur ouvert -> pull-up) */
  GPIO_InitStruct.Pin   = THERM_FLAG_PIN;
  GPIO_InitStruct.Mode  = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull  = GPIO_PULLUP;
  HAL_GPIO_Init(THERM_FLAG_GPIO, &GPIO_InitStruct);

  /* Direction PB10 */
  GPIO_InitStruct.Pin   = MOTOR_DIR_PIN;
  GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull  = GPIO_NOPULL;
  HAL_GPIO_Init(MOTOR_DIR_GPIO, &GPIO_InitStruct);

  /* Frein PB4 (BRAKE LMD18200 actif haut -> 0 = frein relâché) */
  GPIO_InitStruct.Pin   = MOTOR_BRAKE_PIN;
  GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull  = GPIO_NOPULL;
  HAL_GPIO_Init(MOTOR_BRAKE_GPIO, &GPIO_InitStruct);

  HAL_GPIO_WritePin(MOTOR_DIR_GPIO, MOTOR_DIR_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_BRAKE_GPIO, MOTOR_BRAKE_PIN, GPIO_PIN_RESET);
}

/* ============================================================
   Fonctions moteur
   ============================================================ */
void Motor_Forward(void)
{
  HAL_GPIO_WritePin(MOTOR_DIR_GPIO, MOTOR_DIR_PIN, GPIO_PIN_SET);
}

void Motor_Reverse(void)
{
  HAL_GPIO_WritePin(MOTOR_DIR_GPIO, MOTOR_DIR_PIN, GPIO_PIN_RESET);
}

void Motor_Brake(void)
{
  // Sauvegarder la consigne actuelle
  savedSpeed = setSpeed;
  // Mettre la consigne à 0 pour arrêter le moteur
  setSpeed = 0.0f;
  // Réinitialiser l'intégrale
  ui = 0.0f;
}

void Motor_Release(void)
{
  // Restaurer la consigne sauvegardée
  setSpeed = savedSpeed;
  // Réinitialiser l'intégrale pour un redémarrage propre
  ui = 0.0f;
}

/* ============================================================
   Gestion d’erreur
   ============================================================ */
void Error_Handler(void)
{
  __disable_irq();
  while (1) {}
}

/* ============================================================
   Callback UART - appelé à chaque réception d'un octet
   ============================================================ */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART2)
  {
    if (uartRxByte == '\n' || uartRxByte == '\r')
    {
      if (uartRxIndex > 0)
      {
        uartRxBuffer[uartRxIndex] = '\0';
        
        // Copier pour debug
        for (int i = 0; i < uartRxIndex && i < 19; i++)
          lastReceivedBuffer[i] = uartRxBuffer[i];
        lastReceivedBuffer[uartRxIndex] = '\0';
        
        // Vérifier si c'est une commande de direction (commence par 'D')
        if (uartRxBuffer[0] == 'D' && uartRxIndex == 2)
        {
          if (uartRxBuffer[1] == '0')
          {
            motorDirection = 0;
            Motor_Forward();
          }
          else if (uartRxBuffer[1] == '1')
          {
            motorDirection = 1;
            Motor_Reverse();
          }
          newSpeedReceived = 1;  // Pour afficher un message
        }
        // Vérifier si c'est une commande de frein (commence par 'B')
        else if (uartRxBuffer[0] == 'B' && uartRxIndex == 2)
        {
          if (uartRxBuffer[1] == '1')
          {
            // Frein activé : sauvegarder la consigne et mettre à 0
            savedSpeed = setSpeed;
            setSpeed = 0.0f;
            currentSpeed = 0.0f;  // Forcer l'arrêt immédiat
            ui = 0.0f;  // Reset intégrale pour le freinage
          }
          else if (uartRxBuffer[1] == '0')
          {
            // Frein désactivé : restaurer la consigne
            setSpeed = savedSpeed;
            // NE PAS reset currentSpeed - la rampe va gérer la montée progressive
            ui = 0.0f;  // Reset intégrale pour le redémarrage
          }
          newSpeedReceived = 1;  // Pour afficher un message
        }
        // Sinon, c'est une vitesse
        else
        {
          int newSpeed = atoi((char*)uartRxBuffer);
          
          if (newSpeed >= 0 && newSpeed <= 230)
          {
            setSpeed = (float)newSpeed;
            // NE PLUS RÉINITIALISER ui - la rampe de consigne va gérer la transition
            // ui garde sa valeur pour assurer une continuité
            newSpeedReceived = 1;
          }
        }
        uartRxIndex = 0;
      }
      else
      {
        // Si on reçoit juste un \n sans données, réinitialiser
        uartRxIndex = 0;
      }
    }
    else if ((uartRxByte >= '0' && uartRxByte <= '9') || uartRxByte == 'D' || uartRxByte == 'B')
    {
      // Accepter les chiffres ET les lettres 'D' et 'B' pour les commandes
      if (uartRxIndex < sizeof(uartRxBuffer) - 1)
      {
        uartRxBuffer[uartRxIndex++] = uartRxByte;
      }
    }
    else
    {
      uartRxIndex = 0;  // Caractère invalide, réinitialiser
    }
    
    // Relancer la réception du prochain octet
    HAL_UART_Receive_IT(&huart2, (uint8_t*)&uartRxByte, 1);
  }
}

/* ============================================================
   Duty Cycle (0–100 %)
   ============================================================ */
void SetDutyCycle(float percent)
{
  if (percent < 0.0f)  percent = 0.0f;
  if (percent > 100.0f) percent = 100.0f;

  uint32_t pulse = (uint32_t)((percent / 100.0f) * htim1.Init.Period);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pulse);
}
