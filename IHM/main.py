# coding: utf-8
DEBUG=False

import sys
major=sys.version_info.major
minor=sys.version_info.minor
if major==2 and minor==7 :
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
elif major==3 :
    import tkinter as tk
    from tkinter import filedialog
    from tkinter import messagebox
else :
    if __name__ == "__main__" :
        print("Your python version is : ",major,minor)
        print("... I guess it will work !")
    import tkinter as tk
    from tkinter import filedialog
    from tkinter import messagebox 

from pathlib import Path
import pandas as pd
import time
import datetime


from models import Communication
from views import Screen
from controllers import Control
from controllers_csv import ControlCSV
from homepage import HomePage


actions={
        "File" : [
            ("Read from Card","<Control-r>"),
            ("Load","<Control-l>"),
            ("Save","<Control-s>"),
            ("Exit","<Control-e>")
            ],
        "Help" : [
            ("About Us","<Control-u>"),
            ("About Application","<Control-a>"),
            ]
}


class MainWindow(tk.Tk) :
    def __init__(self) :
        tk.Tk.__init__(self)
        self.title("IPS")
        self.option_readfile("main.opt")
        self.menubar()
        
        # Variables pour stocker les composants actuels
        self.current_view = None
        self.current_control = None
        self.model = None
        self.current_mode = None  # 'home', 'live', 'csv'
        
        # Démarrer avec la page d'accueil
        self.show_homepage()

    def clear_window(self):
        """Nettoyer la fenêtre"""
        for widget in self.winfo_children():
            if not isinstance(widget, tk.Menu):  # Garder le menu
                widget.destroy()
        self.current_view = None
        self.current_control = None

    def show_homepage(self):
        """Afficher la page d'accueil"""
        self.clear_window()
        self.current_mode = 'home'
        self.homepage = HomePage(self, self.start_live_mode, self.start_csv_mode)

    def start_live_mode(self):
        """Démarrer le mode lecture temps réel"""
        port = 'COM10'  # Port par défaut
        
        # Vérifier si le port est disponible
        if not Control.check_port_available(port):
            tk.messagebox.showerror(
                "Port non disponible",
                f"Le port {port} n'est pas disponible.\nVérifiez que l'appareil est connecté et que le port est correct."
            )
            return
        
        # Le port est disponible, créer l'interface live
        self.clear_window()
        self.current_mode = 'live'
        self.create_live_interface(port)

    def start_csv_mode(self):
        """Démarrer le mode importation CSV"""
        from tkinter import filedialog
        
        # Demander à l'utilisateur de choisir un fichier CSV
        types = (('CSV files', '*.csv'), ('All files', '*.*'))
        result = filedialog.askopenfilename(filetypes=types, title="Sélectionner un fichier CSV")
        
        if not result:
            # L'utilisateur a annulé
            return
        
        # Charger le fichier CSV
        try:
            data = pd.read_csv(result)
            if 'Vitesses' not in data.columns or 'Intensites' not in data.columns:
                tk.messagebox.showerror(
                    "Format invalide",
                    "Le fichier CSV doit contenir les colonnes 'Vitesses' et 'Intensites'."
                )
                return
            
            # Convertir en liste et s'assurer qu'il n'y a pas de NaN
            vitesses = data['Vitesses'].fillna(0).astype(int).tolist()
            intensites = data['Intensites'].fillna(0).astype(int).tolist()
            
            print(f"Données chargées : {len(vitesses)} points")
            print(f"Vitesses : min={min(vitesses)}, max={max(vitesses)}")
            print(f"Intensités : min={min(intensites)}, max={max(intensites)}")
            
            # Créer l'interface CSV
            self.clear_window()
            self.current_mode = 'csv'
            self.create_csv_interface(vitesses, intensites)
            
        except Exception as e:
            tk.messagebox.showerror(
                "Erreur de chargement",
                f"Impossible de charger le fichier:\n{str(e)}"
            )

    def create_live_interface(self, port):
        """Créer l'interface pour le mode live"""
        self.model = Communication()
        
        # Conteneur principal avec deux colonnes
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Frame gauche pour la visualisation
        left_frame = tk.LabelFrame(main_container, text="Visualisation")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame droite pour les contrôles
        right_frame = tk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Créer la vue dans le frame gauche
        view = Screen(left_frame)
        view.layout()

        self.model.attach(view)

        # Les images de background pour les bouttons
        gauche_img = tk.PhotoImage(file="./assets/gauchepetit.png")
        droite_img = tk.PhotoImage(file="./assets/droite.png")

        # Mise en forme
        gauche_img = gauche_img.subsample(5, 2)
        droite_img = droite_img.subsample(5, 2)

        # Créer les contrôles dans le frame droit
        control = Control(right_frame, self.model, view, droite_img, gauche_img, port)
        control.layout()
        control.view.update_vitesse_repere()
        control.view.update_temps()
        
        self.current_view = view
        self.current_control = control

    def create_csv_interface(self, vitesses, intensites):
        """Créer l'interface pour le mode CSV"""
        self.model = Communication()
        
        # Conteneur principal avec deux colonnes
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Frame gauche pour la visualisation
        left_frame = tk.LabelFrame(main_container, text="Visualisation - Mode CSV")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame droite pour les contrôles
        right_frame = tk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Créer la vue dans le frame gauche
        view = Screen(left_frame)
        view.layout()
        
        # Activer le mode CSV (pas de vitesse de consigne)
        view.is_csv_mode = True
        view.visualisation.delete("vitesse_reference")  # Supprimer la ligne rouge
        
        # Initialiser les données de la vue avec TOUTES les données
        view.vitesses = vitesses.copy()
        view.intensites = intensites.copy()
        view.to_be_actualized = 0  # Mode pause pour permettre la navigation
        
        # Préparer les 100 premières valeurs pour l'affichage
        nb_points = min(100, len(vitesses))
        view.vitesse_a_observer = vitesses[:nb_points]
        view.intensite_a_observer = intensites[:nb_points]
        
        # Compléter avec des zéros si moins de 100 points
        if nb_points < 100:
            view.vitesse_a_observer.extend([0] * (100 - nb_points))
            view.intensite_a_observer.extend([0] * (100 - nb_points))
        
        # Tracer les données initiales selon le mode sélectionné
        view.y_axis_max = 100 if view.observe_vitesse == 1 else 70
        view.update_y_axis()
        
        if view.observe_vitesse == 1:
            view.plot_line(view.vitesse_a_observer, "blue", "data_to_observe")
        else:
            view.plot_line(view.intensite_a_observer, "green", "data_to_observe")
        
        print(f"Vue initialisée avec {len(view.vitesses)} vitesses et {len(view.intensites)} intensités")

        # Les images de background pour les bouttons
        gauche_img = tk.PhotoImage(file="./assets/gauchepetit.png")
        droite_img = tk.PhotoImage(file="./assets/droite.png")

        # Mise en forme
        gauche_img = gauche_img.subsample(5, 2)
        droite_img = droite_img.subsample(5, 2)

        # Créer les contrôles CSV dans le frame droit
        control = ControlCSV(right_frame, self.model, view, droite_img, gauche_img)
        control.layout()
        
        self.current_view = view
        self.current_control = control

    def create(self) :
        # Cette méthode est remplacée par le nouveau système
        pass


    def menubar(self) :
        if DEBUG :
            print("menubar()")
        menubar=tk.Menu(self) 
        self.config(menu=menubar)

        self.menubar_actions(menubar, actions)

        return menubar
    
    def menubar_actions(self, menubar,actions) :
        if DEBUG :
            print("menubar_actions()")
        for key in actions.keys() :
            menu=tk.Menu(menubar)
            for action in actions[key] :
                item,ctrl=action 
                if key=="File" :
                    menu.add_command(label=item,accelerator=ctrl,command=lambda name=item: self.on_file_actions(name))
                    self.bind_all(ctrl,lambda x,name=item: self.on_file_actions(name))
                elif key=="Help" :
                    menu.add_command(label=item,accelerator=ctrl,command=lambda name=item: self.on_help_actions(name))
                    self.bind_all(ctrl,lambda x,name=item: self.on_help_actions(name))
                # if other key ("Help", ...)  : add  callbacks
            menubar.add_cascade(label=key,underline=0,menu=menu)
    
    def on_file_actions(self,name): 
        if DEBUG :
            print("on_file_actions()")  

        if name == "Read from Card":
            self.start_live_mode()
        elif name == "Load" :
            self.start_csv_mode()
        elif name == "Save" :
            self.save_action()
        elif name == "Exit" :
            exit(0)
        else :
            print(name+" : action non implémentée")
        return
    
    def save_action(self) :
        if DEBUG :
            print("save_action()")
        
        if not self.model:
            tk.messagebox.showwarning("Aucune donnée", "Aucune donnée à sauvegarder.")
            return
        
        result = tk.messagebox.askquestion(title="Sauvegarde", message=" Souhaitez-vous sauvegarder le fichier ?")

        if result=='yes' :
            vitesses = self.model.get_vitesse_to_save()
            intensites = self.model.get_intensite_to_save()
            temps = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

            dataframe = {
                "Vitesses": vitesses,
                "Intensites": intensites,
            }

            dataFrame = pd.DataFrame(dataframe)
            file_name = "assets/data/" + str(temps) + "-data.csv"
            dataFrame.to_csv(file_name,index_label="Temps")
            tk.messagebox.showinfo("Succès", f"Fichier sauvegardé : {file_name}")
        return


    def on_help_actions(self,name):
        if DEBUG :
            print("on_help_actions()")
        if  name=="About Us" :
            tk.messagebox.showinfo(title=name, message="Contacts",detail="Email : s25loro@enib.fr")
        elif name=="About Application" :
            print(name)
        else :
            print(name+" : non reconnu")
        return


if __name__=="__main__" :
    app=MainWindow()
    app.mainloop()

class MainWindow(tk.Tk) :
    def __init__(self) :
        tk.Tk.__init__(self)
        self.title("IPS")
        self.option_readfile("main.opt")
        self.menubar()
        self.create()


    def create(self) :
        self.model=Communication()
        frame=tk.LabelFrame(self,name="IPS")
        view=Screen(frame)
        frame.pack()
        view.layout()
        self.model.attach(view)

