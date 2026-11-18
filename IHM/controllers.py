# coding: utf-8
import sys
import serial
major=sys.version_info.major
minor=sys.version_info.minor
if major==2 and minor==7 :
    import Tkinter as tk
    import tkFileDialog as filedialog
elif major==3 :
    import tkinter as tk
    from tkinter import filedialog
else :
    if __name__ == "__main__" :
        print("Your python version is : ",major,minor)
        print("... I guess it will work !")
    import tkinter as tk
    from tkinter import filedialog 

from models import Communication
from views import Screen
from tkinter import ttk
import theme

class Control :
    @staticmethod
    def check_port_available(port):
        """Vérifie si le port COM est disponible"""
        try:
            import serial
            ser = serial.Serial(port, 115200, timeout=0.1)
            ser.close()
            return True
        except Exception as e:
            print(f"Port {port} non disponible: {e}")
            return False
    
    def __init__(self,parent,model,view , droite_bg , gauche_bg, port):
        self.direction = 0
        self.brake = False
        self.gauche_bg = gauche_bg
        self.droite_bg = droite_bg
        self.parent=parent
        self.model=model
        self.view=view
        self.ser = serial.Serial(port, 115200, timeout=0.1)
        self.gui()
        self.actions_binding()
        self.update_from_system()

        self.style = ttk.Style()
        self.style.configure(
            "Custom.TCombobox",
            fieldbackground=theme.SURFACE,
            background=theme.SURFACE_2,
            foreground=theme.TEXT,
            arrowcolor=theme.TEXT,
            bordercolor=theme.BORDER,
            lightcolor=theme.BORDER,
            darkcolor=theme.BORDER,
            padding=6
        )


    def set_direction(self,direction) :
        self.direction = direction
    def get_direction(self) :
        return self.direction

    def set_brake(self,brake) :
        self.brake = brake
    def get_brake(self) :
        return self.brake

    def update_from_system(self):
        line = self.ser.readline().decode('utf-8').strip()
        if line:
            try:
                # Parser le format STM32: "Pos=X Dir=Y RPMout=Z.ZZ Consigne=C Iidx=W V=A.BBV I=C.DDA Duty=E%"
                import re
                rpm_match = re.search(r'RPMout=(\d+)\.?\d*', line)
                current_match = re.search(r'I=(\d+)\.(\d+)A', line)
                consigne_match = re.search(r'Consigne=(\d+)', line)
                
                if rpm_match and current_match:
                    # Extraire la vitesse (RPMout en tr/min)
                    vitesse = int(rpm_match.group(1))
                    
                    # Extraire le courant et convertir en mA (I=0.15A -> 150 mA)
                    amperes = int(current_match.group(1))
                    decimales = int(current_match.group(2))
                    intensite = amperes * 100 + decimales 
                    
                    # Mettre à jour le modèle
                    self.model.set_vitesse(vitesse)
                    self.model.set_intensite(intensite)
                    self.model.update_data_to_save(vitesse, intensite)
                    
                    # Afficher la consigne reçue si disponible
                    if consigne_match:
                        consigne = int(consigne_match.group(1))
                        print(f"Vitesse={vitesse} RPM, Intensité={intensite} mA, Consigne STM32={consigne} RPM")
                    else:
                        print(f"Vitesse={vitesse} RPM, Intensité={intensite} mA")
            except Exception as e:
                # Ignorer les lignes mal formées
                pass
        self.parent.after(100, self.update_from_system)


    def gui(self):
        self.frame=tk.LabelFrame(self.parent,text="Contrôle")
        self.frame_temps = tk.Frame(self.frame)
        self.frame_rotations = tk.Frame(self.frame)
        self.frame_buttons = tk.Frame(self.frame)
        self.frame_calibration = tk.Frame(self.frame)

        self.scale_vitesse()

        self.scale_temps_min()
        self.scale_temps_max()

        self.scale_facteur()
        self.scale_decalage_vertical()

        self.chage_rotation()

        self.pause()
        self.gauche()
        self.droite()
        self.braking()
        self.change_data_to_observe()
    
    def scale_vitesse(self) :
        self.var_vitesse=tk.IntVar()
        self.var_vitesse.set(0)
        self.scale_vitesse=tk.Scale(self.frame,variable=self.var_vitesse,
                             label="Vitesse (RPM)",
                             orient="horizontal",length=500,
                             from_=0,to=230,tickinterval=50,resolution=5)

    def scale_temps_min(self) :
        self.var_temps_min=tk.IntVar()
        self.var_temps_min.set(0)
        self.scale_temps_min=tk.Scale(self.frame_temps,variable=self.var_temps_min,
                             label="Temps debut",
                             orient="horizontal",length=250,
                             from_=0,to=50,tickinterval=10,resolution=1)

    def scale_temps_max(self) :
        self.var_temps_max=tk.IntVar()
        self.var_temps_max.set(0)
        self.scale_temps_max=tk.Scale(self.frame_temps,variable=self.var_temps_max,
                             label="Temps final",
                             orient="horizontal",length=250,
                             from_=50,to=100,tickinterval=10,resolution=1)

    def scale_facteur(self) :
        self.var_facteur=tk.DoubleVar()
        self.var_facteur.set(1.0)
        self.scale_facteur=tk.Scale(self.frame_calibration,variable=self.var_facteur,
                             label="Facteur d'échelle",
                             orient="horizontal",length=250,
                             from_=0.5,to=2.5,tickinterval=0.5,resolution=0.5)

    def scale_decalage_vertical(self) :
        self.var_decalage=tk.IntVar()
        self.var_decalage.set(0)
        self.scale_decalage=tk.Scale(self.frame_calibration,variable=self.var_decalage,
                             label="Décalage vertical",
                             orient="horizontal",length=250,
                             from_=-100,to=100,tickinterval=50,resolution=1)
        self.scale_decalage.config(state="disabled")  # Désactivé par défaut

    def chage_rotation(self) :
        self.change_rotation=ttk.Combobox(
            self.frame_rotations,
            values=["Sens Trigonométrique", "Sens aiguille d'une montre"],
            width=40,
            style="Custom.TCombobox",
        )
        self.change_rotation.set("Sens Trigonométrique")



    def pause(self) :
        self.pause_action = tk.Button(self.frame_buttons, text= "Pause" ,cursor="hand2", padx=20, pady=5, width=10)

    def gauche(self) :
        self.direction_gauche = tk.Button(self.frame_buttons, image=self.gauche_bg, text= "Gauche" ,cursor="hand2", padx=20, pady=5, bg=theme.SURFACE_2, activebackground=theme.BORDER)

    def droite(self) :
        self.direction_droite = tk.Button(self.frame_buttons,image=self.droite_bg, text= "Droite" , cursor="hand2", padx=20, pady=5, bg=theme.SURFACE_2, activebackground=theme.BORDER)

    def change_data_to_observe(self) :
        self.change_data_action = tk.Button(self.frame_buttons, text= "Intensite" ,cursor="hand2", padx=20, pady=5, width=10, bg=theme.SURFACE_2, activebackground=theme.BORDER)

    def braking(self) :
        self.brake_action = tk.Button(self.frame_rotations, text= "Frein" ,cursor="hand2", padx=20, pady=5, width=10, bg=theme.DANGER, activebackground=theme.DANGER_ACTIVE)
        
    def actions_binding(self) :
        self.scale_vitesse.bind("<ButtonRelease-1>",self.on_vitesse_action)
        self.scale_vitesse.bind("<B1-Motion>",self.on_vitesse_motion)
        self.scale_temps_min.bind("<B1-Motion>",self.on_temps_min_action)
        self.scale_temps_max.bind("<B1-Motion>",self.on_temps_max_action)
        self.scale_facteur.bind("<B1-Motion>",self.on_facteur_action)
        self.scale_decalage.bind("<B1-Motion>",self.on_decalage_action)
        self.pause_action.bind("<Button-1>", self.on_pause_action)
        self.direction_gauche.bind("<Button-1>", self.on_gauche_action)
        self.direction_droite.bind("<Button-1>", self.on_droite_action)
        self.brake_action.bind("<Button-1>", self.on_brake_action)
        self.change_rotation.bind("<<ComboboxSelected>>",self.on_change_rotation)
        self.change_data_action.bind("<Button-1>", self.on_change_data_action)

    def on_vitesse_motion(self,event):
        # Mise à jour de la vue pendant le mouvement (sans envoi UART)
        vitesse = self.var_vitesse.get()
        self.view.set_vitesse_repere(vitesse)
        self.view.update_vitesse_repere()

    def on_vitesse_action(self,event):
        # Envoi UART uniquement au relâchement du slider
        vitesse = self.var_vitesse.get()
        print("Vitesse consigne envoyée au STM32 =", vitesse, "RPM")
        self.view.set_vitesse_repere(vitesse)
        self.view.update_vitesse_repere()

        if self.ser.is_open:
            # Vider le buffer d'entrée pour éviter les problèmes
            self.ser.reset_input_buffer()
            msg = f"{vitesse}\n"
            self.ser.write(msg.encode('utf-8'))
            self.ser.flush()  # Forcer l'envoi immédiat
            print(f"Envoi UART: '{msg.strip()}' ({len(msg)} octets)")

    def on_temps_min_action(self,event):
        temps_min = self.var_temps_min.get()
        print("Vitesse = ", temps_min)
        self.view.set_temps_min(temps_min)
        self.view.update_temps()

    def on_temps_max_action(self,event):
        temps_max = self.var_temps_max.get()
        print("Vitesse = ", temps_max)
        self.view.set_temps_max(temps_max)
        self.view.update_temps()

    def on_facteur_action(self,event):
        facteur = self.var_facteur.get()
        print("Facteur d'échelle = ", facteur)
        self.view.set_scale_factor(facteur)
        self.view.update_y_axis()
        # Redessiner la courbe actuelle
        if self.view.observe_vitesse == 1:
            self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def on_decalage_action(self,event):
        # Fonctionne uniquement en pause
        if self.view.to_be_actualized == 0:
            decalage = self.var_decalage.get()
            print("Décalage vertical = ", decalage)
            self.view.set_vertical_offset(decalage)
            # Redessiner les axes avec les nouvelles graduations
            self.view.update_y_axis()
            # Redessiner la courbe actuelle
            if self.view.observe_vitesse == 1:
                self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
            else:
                self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def on_change_rotation(self, event):
        nouveau_sens = self.change_rotation.get()
        if nouveau_sens == "Sens aiguille d'une montre":
            direction = 1
            print("Sens horaire : ", direction)
        else :
            direction = 0
            print("Sens trigonométrique : ", direction)
        
        # Envoyer la direction au STM32
        if self.ser.is_open:
            msg = f"D{direction}\n"  # Format: D0 ou D1
            self.ser.write(msg.encode('utf-8'))
            print(f"Envoi direction: '{msg.strip()}'")

    def on_change_data_action(self, event):
        self.view.observe_vitesse = 0 if self.view.observe_vitesse == 1 else 1
        if self.view.observe_vitesse == 1:
            self.change_data_action.configure(text="Intensite")
        else :
            self.change_data_action.configure(text="Vitesse")
        # Redessiner les axes avec le bon label
        self.view.update_y_axis()

    def on_pause_action(self, event):
        self.view.to_be_actualized  = 0 if self.view.to_be_actualized == 1 else 1
        #self.view.update()

        if self.view.to_be_actualized == 1:
            self.pause_action.configure(text="Pause")
            self.scale_decalage.config(state="disabled")  # Désactiver en mode lecture
        else :
            self.pause_action.configure(text="Play")
            self.scale_decalage.config(state="normal")  # Activer en mode pause

    def on_gauche_action(self,event):
        # self.set_direction(0)
        # print("Direction = ",self.get_direction())
        print("Gauche : ", 1)
        self.view.update_on_gauche()



    def on_droite_action(self,event):
        # self.set_direction(1)
        # print("Direction = ",self.get_direction())

        print("Droite : ", 1)
        self.view.update_on_droite()

    def on_brake_action(self,event):
        self.set_brake(not self.brake)
        if self.brake:
            self.brake_action.configure(text="Démarrer")
            print("Brake = 1")
            # Envoyer commande de freinage au STM32
            try:
                self.ser.reset_input_buffer()
                self.ser.write(b"B1\n")
                print("Envoi UART: 'B1' (Frein activé)")
            except Exception as e:
                print(f"Erreur envoi commande frein: {e}")
        else :
            self.brake_action.configure(text="Frein")
            print("Brake = 0")
            # Envoyer commande de démarrage au STM32
            try:
                self.ser.reset_input_buffer()
                self.ser.write(b"B0\n")
                print("Envoi UART: 'B0' (Frein désactivé)")
            except Exception as e:
                print(f"Erreur envoi commande démarrage: {e}")

    def layout(self,side="top") :
        self.frame.pack(expand=1,padx=5)
        self.scale_vitesse.pack()

        self.frame_temps.pack(pady=6)
        self.scale_temps_min.pack(side="left", padx=(0, 8))
        self.scale_temps_max.pack(side="left")

        self.frame_calibration.pack(pady=6)
        self.scale_facteur.pack(side="left", padx=(0, 8))
        self.scale_decalage.pack(side="left")

        self.frame_rotations.pack(pady=8)
        self.change_rotation.pack(side="left")
        self.brake_action.pack(side="left", padx=5)

        self.frame_buttons.pack(pady=(4, 8))
        self.pause_action.pack(side="left", padx=5)
        self.direction_gauche.pack(side="left", padx=5)
        self.direction_droite.pack(side="left", padx=5)
        self.change_data_action.pack(side="left", padx=5)




if   __name__ == "__main__" :
   root=tk.Tk()
   gauche_img = tk.PhotoImage(file="./assets/gauchepetit.png")
   droite_img = tk.PhotoImage(file="./assets/droite.png")

   gauche_img = gauche_img.subsample(3, 2)
   droite_img = droite_img.subsample(3, 2)
   model=Communication()

   view=Screen(root)
   view.layout()
   model.attach(view)

   model.set_intensite(0)
   model.set_vitesse(0)

   control=Control(root,model,view, droite_img,gauche_img, 'COM4')
   control.layout()
   root.mainloop()

