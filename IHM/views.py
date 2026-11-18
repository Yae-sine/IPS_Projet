# coding: utf-8
DEBUG=False

import sys
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
from observer import Observer
import numpy as np
import theme


def find_last_subarray_index(L, P): # Je veux chercher la liste P dans L
    L = np.asarray(L)
    P = np.asarray(P)
    m = len(P)

    # Générer toutes les fenêtres de taille m
    windows = np.lib.stride_tricks.sliding_window_view(L, m)

    # Comparer toutes les fenêtres
    matches = np.all(windows == P, axis=1)

    # Trouver tous les indices où P apparaît
    indices = np.where(matches)[0]

    if len(indices) == 0:
        return -1

    # Retourner le dernier index
    return indices[-1]


class Screen(Observer) :
    def __init__(self,parent,bg=theme.PLOT_BG,largeur=190,hauteur=78):
        self.parent=parent
        self.bg=bg
        self.largeur,self.hauteur=largeur,hauteur
        self.color="red"
        
        self.to_be_actualized = 1

        self.vitesse_repere = [10 for i in range(0, 100)]
        self.vitesses = [1 for i in range(0, 100)]
        self.intensites = [1 for i in range(0, 100)]
        self.observe_vitesse = 1

        self.vitesse_a_observer = []
        self.intensite_a_observer = []

        self.temps_min = 10
        self.temps_max = 90

        # Attributs de calibration (initialiser AVANT draw_axes)
        self.scale_factor = 1.0  # Facteur de division (0.5, 1, 1.5, 2)
        self.vertical_offset = 0  # Décalage vertical (-100 à +100)
        self.y_axis_max = 100  # Valeur max de l'axe Y (100 pour vitesse, 70 pour intensité)
        self.is_csv_mode = False  # Mode CSV (pas de vitesse de consigne)
        
        # Créer l'interface après avoir initialisé les attributs
        self.gui() 
        self.actions_binding()
        self.draw_axes()


    def get_vitesses(self):
        return self.vitesses
    def get_intensites(self):
        return self.intensites

    def get_vitesse_repere(self):
        return self.vitesse_repere

    def get_temps_min(self):
        return self.temps_min
    def get_temps_max(self):
        return self.temps_max

    def set_vitesse_repere(self,vitesse_repere) :
        self.vitesse_repere=[vitesse_repere for i in range(0,100)]

    def set_vitesses(self,vitesse):
        self.vitesses.append(vitesse)

    def set_intensites(self,intensite):
        self.intensites.append(intensite)


    def set_temps_min(self, temps):
        self.temps_min = temps

    def set_temps_max(self, temps):
        self.temps_max = temps

    def get_scale_factor(self):
        return self.scale_factor
    def set_scale_factor(self, factor):
        self.scale_factor = factor

    def get_vertical_offset(self):
        return self.vertical_offset
    def set_vertical_offset(self, offset):
        self.vertical_offset = offset

    def get_y_axis_max(self):
        return self.y_axis_max
    def set_y_axis_max(self, y_max):
        self.y_axis_max = y_max


    def get_parent(self) :
        return self.parent
    def set_parent(self,parent) :
        self.parent=parent
    def gui(self) :
        self.frame = tk.Frame(self.parent, bg=theme.BG)

        kpi = dict(width=self.largeur, height=self.hauteur, bg=theme.SURFACE,
                   highlightthickness=1, highlightbackground=theme.BORDER)
        self.vitesse = tk.Canvas(self.frame, **kpi)
        self.intensite = tk.Canvas(self.frame, **kpi)

        self.temps_aservissement = tk.Canvas(self.frame, **kpi)

        self.visualisation=tk.Canvas(self.parent,bg=self.bg,width=600,height=300,
                                     highlightthickness=1, highlightbackground=theme.BORDER)
        # Les textes de valeur sont créés en premier dans chaque canvas
        # (même identifiant d'item dans les trois canvas).
        value_y = int(self.hauteur * 0.64)
        self.text_vitesse = self.vitesse.create_text(
            self.largeur - 14, value_y,
            text="--", fill=theme.SPEED, font=theme.FONT_KPI, anchor="e"
        )
        self.text_intensite = self.intensite.create_text(
            self.largeur - 14, value_y,
            text="--", fill=theme.CURRENT, font=theme.FONT_KPI, anchor="e"
        )
        self.text_temps_aservissement = self.temps_aservissement.create_text(
            self.largeur - 14, value_y,
            text="--", fill=theme.MARKER, font=theme.FONT_KPI, anchor="e"
        )

        # Titres et barre de couleur des cartes
        for canvas, caption, color in (
            (self.vitesse, "VITESSE", theme.SPEED),
            (self.intensite, "COURANT", theme.CURRENT),
            (self.temps_aservissement, "TEMPS D'ASSERV.", theme.MARKER),
        ):
            canvas.create_rectangle(0, 0, 4, self.hauteur + 2, fill=color, outline="")
            canvas.create_text(16, 16, text=caption, fill=theme.MUTED,
                               font=theme.FONT_CAPTION, anchor="w")

    def actions_binding(self) :
        if DEBUG :
            print(type(self).__name__+".actions_binding()")
        
    def update(self,subject):
        if subject:
            vitesse = subject.get_vitesse()
            intensite = subject.get_intensite()

            if vitesse is not None and intensite is not None:
                self.vitesse.itemconfig(self.text_vitesse, text=str(vitesse) + " t/m")
                self.intensite.itemconfig(self.text_intensite, text=str(intensite*10) + " mA")
            else:
                self.vitesse.itemconfig(self.text_vitesse, text="--")
                self.intensite.itemconfig(self.text_intensite, text="--")

            #tracer la courbe des vitesses
            self.set_vitesses(vitesse)  # pour garder les vraies valeurs j'actualise toujours
            self.set_intensites(intensite)

            if self.to_be_actualized == 1:
                self.vitesse_a_observer = self.get_vitesses()[-100:].copy()
                self.intensite_a_observer = self.get_intensites()[-100:].copy()

            if self.observe_vitesse == 1 :
                self.y_axis_max = 100  # Vitesse : 0-100 (après calibration)
                self.plot_line(self.vitesse_a_observer, "blue", "data_to_observe")
            else :
                self.y_axis_max = 70  # Intensité : 0-70
                self.plot_line(self.intensite_a_observer, "green", "data_to_observe")
            
            # Redessiner les axes si nécessaire
            self.update_y_axis()

        else:
            self.vitesse.itemconfig(self.text_vitesse, text="N/A")
            self.intensite.itemconfig(self.text_intensite, text="N/A")

    # à implementer
    def update_on_gauche(self):
        if self.to_be_actualized == 0:
            vitesses = self.get_vitesses().copy()
            intensites = self.get_intensites().copy()

            indice_de_data = find_last_subarray_index(vitesses,self.vitesse_a_observer)
            print(f"Index actuel: {indice_de_data}")
            
            # Vérifier si on peut aller à gauche (pas au début)
            if indice_de_data != -1 and indice_de_data > 0:
                new_index = indice_de_data - 1
                # S'assurer qu'on a assez de données
                if new_index >= 0 and new_index + 100 <= len(vitesses):
                    self.vitesse_a_observer = vitesses[new_index:new_index+100].copy()
                    self.intensite_a_observer = intensites[new_index:new_index+100].copy()
                    if self.observe_vitesse == 1:
                        self.plot_line(self.vitesse_a_observer, "blue", "data_to_observe")
                    else:
                        self.plot_line(self.intensite_a_observer, "green", "data_to_observe")
                else:
                    print("Début des données atteint")
            else:
                print("Impossible de naviguer à gauche - déjà au début")

    def update_on_droite(self):
        if self.to_be_actualized == 0:
            vitesses = self.get_vitesses().copy()
            intensites = self.get_intensites().copy()

            indice_de_data = find_last_subarray_index(vitesses,self.vitesse_a_observer)
            print(f"Index actuel: {indice_de_data}")
            
            # Vérifier si on peut aller à droite (pas à la fin)
            if indice_de_data != -1:
                new_index = indice_de_data + 1
                # S'assurer qu'on ne dépasse pas la fin
                if new_index + 100 <= len(vitesses):
                    self.vitesse_a_observer = vitesses[new_index:new_index+100].copy()
                    self.intensite_a_observer = intensites[new_index:new_index+100].copy()
                    if self.observe_vitesse == 1:
                        self.plot_line(self.vitesse_a_observer, "blue", "data_to_observe")
                    else:
                        self.plot_line(self.intensite_a_observer, "green", "data_to_observe")
                else:
                    print("Fin des données atteinte")
            else:
                print("Impossible de naviguer à droite - position inconnue")

    def update_vitesse_repere(self):
        if self.to_be_actualized == 1 and not self.is_csv_mode:
            # Tracer la ligne de la vitesse repere (sauf en mode CSV)
            self.plot_line(self.get_vitesse_repere(), "red", "vitesse_reference")
            print(self.get_vitesse_repere())
        elif self.is_csv_mode:
            # Supprimer la ligne de référence en mode CSV
            self.visualisation.delete("vitesse_reference")

    def update_temps(self):
        temps_min = self.get_temps_min()
        temps_max = self.get_temps_max()

        if temps_min and temps_max:
            self.tracer_axes_temps(self.get_temps_min(),"temps_min")
            self.tracer_axes_temps(self.get_temps_max(),"temps_max")

            self.temps_aservissement.itemconfig(self.text_vitesse, text=str((temps_max-temps_min)/5) + " s")

        else:
            self.temps_aservissement.itemconfig(self.text_vitesse, text="--")
            print("temps_max ou temps min non defini")



    def plot_line(self, vitesses, color, name):
        width = 600
        height = 300
        margin_x = 40
        margin_y = 20

        coords = []
        for t, v in enumerate(vitesses):
            # Appliquer la calibration : diviser par le facteur d'échelle
            v_scaled = v / self.scale_factor
            # Appliquer le décalage vertical
            v_adjusted = v_scaled + self.vertical_offset
            
            # Conversion vers coordonnées Canvas
            x = margin_x + (t / 100) * (width - margin_x - 10)
            # Normaliser par rapport à y_axis_max au lieu de 100
            y = height - margin_y - (v_adjusted / self.y_axis_max) * (height - margin_y - 10)
            coords.extend((x, y))
        color = theme.CURVE_COLORS.get(color, color)
        dash = (6, 4) if name == "vitesse_reference" else None
        self.visualisation.delete(name)
        self.visualisation.create_line(coords, fill=color, smooth=1, width=2, dash=dash,
                                       capstyle="round", joinstyle="round", tags=name)

    def tracer_axes_temps(self, temps, name ):
        # height = int(self.visualisation['height'])
        height = 300
        width = 600
        margin_x = 40
        t =margin_x +  (temps / 100) * (width - margin_x - 10)
        self.visualisation.delete(name)
        self.visualisation.create_line(t, 10, t, height - 20, fill=theme.MARKER, width=1, dash=(3, 3), tags=name)

    def resize(self,event):
        if DEBUG :
            print(type(self).__name__+".resize()")
            print("width,height : ",(event.width,event.height))
        self.width,self.height=event.width,event.height
        # TODO : manage grid and signal refresh in resizing()

    def update_y_axis(self):
        """Redessine les axes avec la nouvelle échelle Y"""
        self.draw_axes()
        # Redessiner la vitesse de référence si elle existe (sauf en mode CSV)
        if hasattr(self, 'vitesse_repere') and not self.is_csv_mode:
            self.plot_line(self.get_vitesse_repere(), "red", "vitesse_reference")
        elif self.is_csv_mode:
            # Supprimer la ligne de référence en mode CSV
            self.visualisation.delete("vitesse_reference")

    def draw_axes(self):
        width = 600
        height = 300
        margin_x = 40
        margin_y = 20

        self.visualisation.delete("axes")

        # Grille de fond
        for i in range(20, 101, 20):
            x = margin_x + (i / 100) * (width - margin_x - 10)
            self.visualisation.create_line(x, 10, x, height - margin_y, fill=theme.GRID, tags=("axes", "grid"))
        for k in range(1, 6):
            y = height - margin_y - (k / 5) * (height - margin_y - 10)
            self.visualisation.create_line(margin_x, y, width - 10, y, fill=theme.GRID, tags=("axes", "grid"))

        self.visualisation.create_line(margin_x, height - margin_y, width - 10, height - margin_y, width=1, arrow=tk.LAST, tags="axes", fill=theme.AXIS)
        self.visualisation.create_line(margin_x, height - margin_y, margin_x, 10, width=1, arrow=tk.LAST, tags="axes", fill=theme.AXIS)

        # Label des axes - dynamique selon ce qui est observé
        self.visualisation.create_text(width - 20, height - 8, text="t (s)", font=theme.FONT_SMALL, tags="axes", fill=theme.MUTED)
        if self.observe_vitesse == 1:
            y_label = "V (RPM)"
        else:
            y_label = "I (mA)"
        self.visualisation.create_text(margin_x + 6, 12, text=y_label, font=theme.FONT_CAPTION, tags="axes", fill=theme.MUTED, anchor="w")

        # Axe X : temps (0-100 échantillons = 0-20 secondes à 5 Hz)
        for i in range(0, 101, 20):
            x = margin_x + (i / 100) * (width - margin_x - 10)
            self.visualisation.create_line(x, height - margin_y, x, height - margin_y + 4, tags="axes" , fill=theme.AXIS)
            # Convertir échantillons en secondes (100 échantillons = 20s car 5 échantillons/s)
            time_seconds = i / 5
            self.visualisation.create_text(x, height - margin_y + 12, text=str(int(time_seconds)), font=theme.FONT_SMALL, tags="axes", fill=theme.MUTED)

        # Axe Y : valeur (dynamique selon y_axis_max ET scale_factor)
        # Calculer la valeur max réelle affichée (en tenant compte du facteur d'échelle)
        max_displayed = self.y_axis_max
        
        # Déterminer le pas en fonction de y_axis_max
        if self.y_axis_max == 100:
            step = 20  # Pour vitesse: 0, 20, 40, 60, 80, 100
        else:  # y_axis_max == 70
            step = 14  # Pour intensité: 0, 14, 28, 42, 56, 70
        
        for i in range(0, int(max_displayed) + 1, step):
            y = height - margin_y - (i / self.y_axis_max) * (height - margin_y - 10)
            self.visualisation.create_line(margin_x - 4, y, margin_x, y, tags="axes" , fill=theme.AXIS)
            # Afficher la valeur réelle en tenant compte du scale_factor ET du vertical_offset
            real_value = int(i * self.scale_factor - self.vertical_offset * self.scale_factor)
            self.visualisation.create_text(margin_x - 8, y, text=str(real_value), font=theme.FONT_SMALL, tags="axes", fill=theme.MUTED, anchor="e")

        self.visualisation.tag_lower("grid")

    def layout(self) :
        self.frame.pack(padx=8, pady=(4, 10), anchor="w")
        self.vitesse.pack(side="left", padx=(0, 10))
        self.intensite.pack(side="left", padx=(0, 10))
        self.temps_aservissement.pack(side="left")
        self.visualisation.pack(side="left", padx=8, pady=(0, 8))

if   __name__ == "__main__" :
   root=tk.Tk()
   model=Communication()
   model.set_intensite(100)

   model.set_vitesse(150)

   view=Screen(root)
   view.layout()

   model.attach(view)
   model.notify()
   view.update_vitesse_repere()
   view.update_temps()

   root.mainloop()

