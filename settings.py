# -*- coding: utf-8 -*-
"""
Système de gestion des paramètres pour MultiScreenCapt-Clikdoo-v1.0
"""

import json
import os
from pathlib import Path

class Settings:
    def __init__(self):
        self.settings_file = Path.home() / '.multiscreencapt_clikdoo_settings.json'
        self.default_settings = {
            'language': 'en',  # Par défaut en anglais
            'save_directory': str(Path.home() / 'Pictures' / 'MultiScreenCapt-Clikdoo'),
            'custom_screen_names': {},  # Dictionnaire pour sauvegarder les noms personnalisés
            'saved_paths': []  # Liste des chemins sauvegardés
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Charge les paramètres depuis le fichier"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Fusionner avec les paramètres par défaut
                    merged_settings = self.default_settings.copy()
                    merged_settings.update(settings)
                    return merged_settings
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"Erreur lors du chargement des paramètres: {e}")
            return self.default_settings.copy()
    
    def save_settings(self):
        """Sauvegarde les paramètres dans le fichier"""
        try:
            # Créer le dossier parent si nécessaire
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres: {e}")
    
    def get(self, key, default=None):
        """Récupère une valeur de paramètre"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Définit une valeur de paramètre et sauvegarde"""
        self.settings[key] = value
        self.save_settings()
    
    def get_language(self):
        """Récupère la langue actuelle"""
        return self.get('language', 'en')
    
    def set_language(self, language):
        """Définit la langue et sauvegarde"""
        self.set('language', language)
    
    def get_default_save_directory(self):
        """Retourne le chemin par défaut (dépend de l'utilisateur courant)."""
        default = Path.home() / 'Pictures' / 'MultiScreenCapt-Clikdoo'
        return str(default)
    
    def get_save_directory(self):
        """Récupère le dossier de sauvegarde avec fallback robuste.
        - Utilise la valeur persistée si valide
        - Sinon retombe sur le chemin par défaut et le crée si nécessaire
        """
        saved = self.get('save_directory', self.get_default_save_directory())
        try:
            path_obj = Path(saved).expanduser()
            if not path_obj.exists():
                # Fallback sur le défaut et création du dossier
                path_obj = Path(self.get_default_save_directory())
                path_obj.mkdir(parents=True, exist_ok=True)
                self.set('save_directory', str(path_obj))
            return str(path_obj)
        except Exception:
            # En cas d'erreur inattendue, retomber sur le défaut
            path_obj = Path(self.get_default_save_directory())
            path_obj.mkdir(parents=True, exist_ok=True)
            self.set('save_directory', str(path_obj))
            return str(path_obj)
    
    def set_save_directory(self, directory):
        """Définit le dossier de sauvegarde et sauvegarde"""
        print(f"DEBUG Settings: set_save_directory appelé avec: {directory}")
        try:
            self.set('save_directory', directory)
            print(f"DEBUG Settings: save_directory mis à jour avec succès")
        except Exception as e:
            print(f"DEBUG Settings: Erreur dans set_save_directory: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_custom_screen_names(self):
        """Récupère les noms d'écrans personnalisés"""
        return self.get('custom_screen_names', {})
    
    def set_custom_screen_names(self, screen_names):
        """Définit les noms d'écrans personnalisés et sauvegarde"""
        self.set('custom_screen_names', screen_names)
    
    def reset_custom_screen_names(self):
        """Réinitialise les noms d'écrans personnalisés"""
        self.set('custom_screen_names', {})
    
    def get_saved_paths(self):
        """Récupère la liste des chemins sauvegardés"""
        return self.get('saved_paths', [])
    
    def save_paths(self, paths):
        """Sauvegarde la liste des chemins"""
        self.set('saved_paths', paths) 