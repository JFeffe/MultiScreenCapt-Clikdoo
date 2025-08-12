#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour isoler le problème du bouton Browse
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from pathlib import Path

class TestSettings:
    def __init__(self):
        self.settings_file = Path.home() / '.test_settings.json'
        self.default_settings = {
            'save_directory': str(Path.home() / 'Pictures' / 'Test')
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    merged_settings = self.default_settings.copy()
                    merged_settings.update(settings)
                    return merged_settings
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"Erreur lors du chargement des paramètres: {e}")
            return self.default_settings.copy()
    
    def save_settings(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres: {e}")
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
    
    def get_save_directory(self):
        return self.get('save_directory', str(Path.home() / 'Pictures' / 'Test'))
    
    def set_save_directory(self, directory):
        print(f"DEBUG Settings: set_save_directory appelé avec: {directory}")
        try:
            self.set('save_directory', directory)
            print(f"DEBUG Settings: save_directory mis à jour avec succès")
        except Exception as e:
            print(f"DEBUG Settings: Erreur dans set_save_directory: {e}")
            import traceback
            traceback.print_exc()
            raise

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Browse Button")
        self.root.geometry("600x400")
        
        # Initialiser les paramètres
        self.settings = TestSettings()
        self.save_directory = self.settings.get_save_directory()
        
        # Créer l'interface
        self.create_interface()
    
    def create_interface(self):
        # Frame principal
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = tk.Label(main_frame, text="Test du bouton Browse", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Frame pour les contrôles
        controls_frame = tk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Label et entry pour le dossier de sauvegarde
        save_label = tk.Label(controls_frame, text="Dossier de sauvegarde:")
        save_label.pack(anchor=tk.W)
        
        self.save_path_var = tk.StringVar(value=self.save_directory)
        save_entry = tk.Entry(controls_frame, textvariable=self.save_path_var, width=50)
        save_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Bouton Browse
        browse_button = tk.Button(controls_frame, text="Browse", command=self.browse_save_directory)
        browse_button.pack(pady=(0, 10))
        
        # Zone de log
        log_label = tk.Label(main_frame, text="Log de débogage:")
        log_label.pack(anchor=tk.W, pady=(20, 5))
        
        self.log_text = tk.Text(main_frame, height=15, width=70)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar pour le log
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # Bouton pour effacer le log
        clear_button = tk.Button(main_frame, text="Effacer le log", command=self.clear_log)
        clear_button.pack(pady=(10, 0))
    
    def log(self, message):
        """Ajoute un message au log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def clear_log(self):
        """Efface le log"""
        self.log_text.delete(1.0, tk.END)
    
    def browse_save_directory(self):
        """Ouvre un dialogue pour choisir le dossier de sauvegarde"""
        self.log("DEBUG: Début de browse_save_directory")
        try:
            self.log(f"DEBUG: save_directory actuel: {self.save_directory}")
            self.log("DEBUG: Ouverture du dialogue filedialog.askdirectory...")
            
            # Forcer la mise à jour de l'interface avant d'ouvrir le dialogue
            self.root.update()
            
            directory = filedialog.askdirectory(initialdir=self.save_directory)
            self.log(f"DEBUG: Dialogue fermé, directory sélectionné: {directory}")
            
            if directory:
                self.log("DEBUG: Mise à jour du save_directory...")
                self.save_directory = directory
                self.log("DEBUG: Mise à jour de save_path_var...")
                self.save_path_var.set(directory)
                self.log("DEBUG: Sauvegarde dans les paramètres...")
                # Sauvegarder le nouveau répertoire dans les paramètres
                self.settings.set_save_directory(directory)
                self.log(f"DEBUG: Dossier de sauvegarde mis à jour avec succès: {directory}")
            else:
                self.log("DEBUG: Aucun dossier sélectionné")
        except Exception as e:
            self.log(f"DEBUG: Exception dans browse_save_directory: {e}")
            self.log(f"DEBUG: Type d'exception: {type(e)}")
            import traceback
            traceback_str = traceback.format_exc()
            self.log(f"DEBUG: Traceback:\n{traceback_str}")
            messagebox.showerror("Erreur", f"Erreur lors de la sélection du dossier: {e}")
        self.log("DEBUG: Fin de browse_save_directory")

def main():
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 