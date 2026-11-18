# coding: utf-8
import sys
major=sys.version_info.major
minor=sys.version_info.minor
if major==2 and minor==7 :
    import Tkinter as tk
elif major==3 :
    import tkinter as tk
else :
    import tkinter as tk

from tkinter import ttk

class ControlCSV:
    """Contrôleur simplifié pour le mode CSV (pas de lecture en temps réel)"""
    def __init__(self, parent, model, view, droite_bg, gauche_bg):
        self.parent = parent
        self.model = model
        self.view = view
        self.gauche_bg = gauche_bg
        self.droite_bg = droite_bg
        self.gui()
        self.actions_binding()

    def gui(self):
        self.frame = tk.LabelFrame(self.parent, text="Contrôles")
        self.frame_temps = tk.Frame(self.frame)
        self.frame_calibration = tk.Frame(self.frame)
        self.frame_navigation = tk.Frame(self.frame)
        self.frame_buttons = tk.Frame(self.frame)

        self.scale_temps_min()
        self.scale_temps_max()
        
        self.scale_facteur()
        self.scale_decalage_vertical()
        
        self.gauche()
        self.droite()
        self.change_data_to_observe()

    def scale_temps_min(self):
        self.var_temps_min = tk.IntVar()
        self.var_temps_min.set(0)
        self.scale_temps_min = tk.Scale(
            self.frame_temps,
            variable=self.var_temps_min,
            label="Temps début",
            orient="horizontal",
            length=250,
            from_=0,
            to=50,
            tickinterval=10,
            resolution=1
        )

    def scale_temps_max(self):
        self.var_temps_max = tk.IntVar()
        self.var_temps_max.set(0)
        self.scale_temps_max = tk.Scale(
            self.frame_temps,
            variable=self.var_temps_max,
            label="Temps final",
            orient="horizontal",
            length=250,
            from_=50,
            to=100,
            tickinterval=10,
            resolution=1
        )

    def scale_facteur(self):
        self.var_facteur = tk.DoubleVar()
        self.var_facteur.set(1.0)
        self.scale_facteur = tk.Scale(
            self.frame_calibration,
            variable=self.var_facteur,
            label="Facteur d'échelle",
            orient="horizontal",
            length=250,
            from_=0.5,
            to=2.5,
            tickinterval=0.5,
            resolution=0.5
        )

    def scale_decalage_vertical(self):
        self.var_decalage = tk.IntVar()
        self.var_decalage.set(0)
        self.scale_decalage = tk.Scale(
            self.frame_calibration,
            variable=self.var_decalage,
            label="Décalage vertical",
            orient="horizontal",
            length=250,
            from_=-100,
            to=100,
            tickinterval=50,
            resolution=1
        )

    def gauche(self):
        self.direction_gauche = tk.Button(
            self.frame_navigation,
            image=self.gauche_bg,
            text="Gauche",
            cursor="hand2",
            padx=20,
            pady=5
        )

    def droite(self):
        self.direction_droite = tk.Button(
            self.frame_navigation,
            image=self.droite_bg,
            text="Droite",
            cursor="hand2",
            padx=20,
            pady=5
        )

    def change_data_to_observe(self):
        self.change_data_action = tk.Button(
            self.frame_buttons,
            text="Intensité",
            cursor="hand2",
            padx=20,
            pady=5,
            width=10
        )

    def actions_binding(self):
        self.scale_temps_min.bind("<B1-Motion>", self.on_temps_min_action)
        self.scale_temps_max.bind("<B1-Motion>", self.on_temps_max_action)
        self.scale_facteur.bind("<B1-Motion>", self.on_facteur_action)
        self.scale_decalage.bind("<B1-Motion>", self.on_decalage_action)
        self.direction_gauche.bind("<Button-1>", self.on_gauche_action)
        self.direction_droite.bind("<Button-1>", self.on_droite_action)
        self.change_data_action.bind("<Button-1>", self.on_change_data_action)

    def on_temps_min_action(self, event):
        temps_min = self.var_temps_min.get()
        print("Temps min = ", temps_min)
        self.view.set_temps_min(temps_min)
        self.view.update_temps()

    def on_temps_max_action(self, event):
        temps_max = self.var_temps_max.get()
        print("Temps max = ", temps_max)
        self.view.set_temps_max(temps_max)
        self.view.update_temps()

    def on_facteur_action(self, event):
        facteur = self.var_facteur.get()
        print("Facteur d'échelle = ", facteur)
        self.view.set_scale_factor(facteur)
        self.view.update_y_axis()
        # Redessiner la courbe actuelle
        if self.view.observe_vitesse == 1:
            self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def on_decalage_action(self, event):
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

    def on_change_data_action(self, event):
        self.view.observe_vitesse = 0 if self.view.observe_vitesse == 1 else 1
        if self.view.observe_vitesse == 1:
            self.change_data_action.configure(text="Intensité")
            self.view.y_axis_max = 100
        else:
            self.change_data_action.configure(text="Vitesse")
            self.view.y_axis_max = 70
        
        # Redessiner les axes avec le bon label
        self.view.update_y_axis()
        
        # Redessiner la courbe correspondante
        if self.view.observe_vitesse == 1:
            self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def on_gauche_action(self, event):
        print("Navigation gauche")
        # En mode CSV, on est toujours en mode navigation
        self.view.to_be_actualized = 0
        self.view.update_on_gauche()
        # Redessiner après navigation
        if self.view.observe_vitesse == 1:
            self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def on_droite_action(self, event):
        print("Navigation droite")
        # En mode CSV, on est toujours en mode navigation
        self.view.to_be_actualized = 0
        self.view.update_on_droite()
        # Redessiner après navigation
        if self.view.observe_vitesse == 1:
            self.view.plot_line(self.view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            self.view.plot_line(self.view.intensite_a_observer, "green", "data_to_observe")

    def layout(self, side="top"):
        self.frame.pack(expand=1, padx=5)

        self.frame_temps.pack(pady=2)
        self.scale_temps_min.pack(side="left")
        self.scale_temps_max.pack(side="left")

        self.frame_calibration.pack(pady=2)
        self.scale_facteur.pack(side="left")
        self.scale_decalage.pack(side="left")

        self.frame_navigation.pack(pady=2)
        self.direction_gauche.pack(side="left", padx=5)
        self.direction_droite.pack(side="left", padx=5)

        self.frame_buttons.pack(pady=2)
        self.change_data_action.pack(side="left", padx=5)
