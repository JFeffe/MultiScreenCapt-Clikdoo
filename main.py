import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
from PIL import Image, ImageTk
import os
from datetime import datetime
import screeninfo
import subprocess
import re
import mss
import mss.tools
import win32gui
import win32con
import win32ui
import win32api
from pywinauto import Desktop
from translations import get_text
from settings import Settings
import json
from pathlib import Path
import threading
import queue
import time

class SmartCapture:
    def __init__(self, root):
        self.root = root
        self.settings = Settings()
        self.current_language = self.settings.get_language()
        
        # Mettre à jour le titre de la fenêtre
        self.root.title(get_text(self.current_language, 'app_title'))
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.save_directory = self.settings.get_save_directory()
        self.screens = []
        self.windows = []
        
        # Créer le dossier de sauvegarde s'il n'existe pas
        os.makedirs(self.save_directory, exist_ok=True)
        
        # Détecter les écrans
        self.detect_screens()
        
        # Détecter les fenêtres
        self.detect_windows()
        
        # Créer l'interface
        self.create_interface()
        
    def get_screen_names(self):
        """Récupère les noms des écrans via plusieurs méthodes avancées"""
        try:
            print("Début de la détection des noms d'écrans...")
            all_names = []
            
            # Méthode 1: WmiMonitorID (noms conviviaux)
            cmd1 = [
                'powershell',
                '-Command',
                '''
                $monitors = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorID
                $names = @()
                foreach ($monitor in $monitors) {
                    $name = ""
                    foreach ($char in $monitor.UserFriendlyName) {
                        if ($char -ne 0) {
                            $name += [char]$char
                        }
                    }
                    $name = $name.Trim()
                    if ($name -ne "") {
                        $names += $name
                    }
                }
                $names
                '''
            ]
            
            # Méthode 2: Win32_DesktopMonitor (noms système)
            cmd2 = [
                'powershell',
                '-Command',
                '''
                $monitors = Get-WmiObject -Class Win32_DesktopMonitor | Where-Object {$_.Availability -eq 3}
                $names = @()
                foreach ($monitor in $monitors) {
                    if ($monitor.Name -and $monitor.Name -ne "Generic PnP Monitor") {
                        $names += $monitor.Name
                    }
                }
                $names
                '''
            ]
            
            # Méthode 3: Win32_VideoController (informations détaillées)
            cmd3 = [
                'powershell',
                '-Command',
                '''
                $controllers = Get-WmiObject -Class Win32_VideoController | Where-Object {$_.CurrentHorizontalResolution -gt 0}
                $names = @()
                foreach ($controller in $controllers) {
                    if ($controller.Name -and $controller.Name -ne "Generic PnP Monitor") {
                        $names += $controller.Name
                    }
                }
                $names
                '''
            ]
            
            # Méthode 4: Utiliser l'API Windows Display
            cmd4 = [
                'powershell',
                '-Command',
                '''
                Add-Type -AssemblyName System.Windows.Forms
                $screens = [System.Windows.Forms.Screen]::AllScreens
                $names = @()
                foreach ($screen in $screens) {
                    $names += "Display " + $screen.DeviceName
                }
                $names
                '''
            ]
            
            # Méthode 5: Registre Windows pour les moniteurs
            cmd5 = [
                'powershell',
                '-Command',
                '''
                $monitors = Get-ItemProperty "HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\DISPLAY\\*\\*" | Where-Object {$_.FriendlyName}
                $names = @()
                foreach ($monitor in $monitors) {
                    if ($monitor.FriendlyName -and $monitor.FriendlyName -ne "Generic PnP Monitor") {
                        $names += $monitor.FriendlyName
                    }
                }
                $names
                '''
            ]
            
            # Méthode 6: Utiliser Get-CimInstance pour plus de détails
            cmd6 = [
                'powershell',
                '-Command',
                '''
                $monitors = Get-CimInstance -ClassName WmiMonitorID -Namespace root\\wmi
                $names = @()
                foreach ($monitor in $monitors) {
                    $name = ""
                    foreach ($char in $monitor.UserFriendlyName) {
                        if ($char -ne 0) {
                            $name += [char]$char
                        }
                    }
                    $name = $name.Trim()
                    if ($name -ne "") {
                        $names += $name
                    }
                }
                $names
                '''
            ]
            
            # Essayer toutes les méthodes
            for i, cmd in enumerate([cmd1, cmd2, cmd3, cmd4, cmd5, cmd6]):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
                    if result.returncode == 0 and result.stdout.strip():
                        names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
                        all_names.extend(names)
                        print(f"Méthode {i+1} détectée: {names}")
                except Exception as e:
                    print(f"Erreur méthode {i+1}: {e}")
            
            # Supprimer les doublons et nettoyer
            unique_names = []
            for name in all_names:
                if name not in unique_names and name != "Generic PnP Monitor":
                    # Nettoyer les noms du registre Windows
                    if "Generic Monitor (" in name and ")" in name:
                        # Extraire le nom entre parenthèses
                        start = name.find("(") + 1
                        end = name.find(")")
                        if start > 0 and end > start:
                            clean_name = name[start:end]
                            if clean_name not in unique_names:
                                unique_names.append(clean_name)
                    else:
                        unique_names.append(name)
            
            print(f"Tous les noms détectés: {unique_names}")
            return unique_names
            
        except Exception as e:
            print(f"Erreur lors de la récupération des noms d'écrans: {e}")
            # En cas d'erreur, retourner une liste vide pour éviter le plantage
            return []
        finally:
            print("Fin de la détection des noms d'écrans")
        return []
    
    def get_edid_names(self):
        """Récupère les noms d'écrans via les informations EDID"""
        try:
            cmd = [
                'powershell',
                '-Command',
                '''
                # Fonction pour convertir les bytes EDID en string
                function Convert-EDIDToString {
                    param([byte[]]$Bytes)
                    $result = ""
                    for ($i = 0; $i -lt $Bytes.Length; $i++) {
                        if ($Bytes[$i] -ne 0) {
                            $result += [char]$Bytes[$i]
                        }
                    }
                    return $result.Trim()
                }

                # Récupérer les informations EDID
                $monitors = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorID
                $names = @()
                
                foreach ($monitor in $monitors) {
                    # Essayer UserFriendlyName d'abord
                    if ($monitor.UserFriendlyName) {
                        $name = Convert-EDIDToString $monitor.UserFriendlyName
                        if ($name -ne "") {
                            $names += $name
                            continue
                        }
                    }
                    
                    # Essayer ProductCodeName
                    if ($monitor.ProductCodeName) {
                        $name = Convert-EDIDToString $monitor.ProductCodeName
                        if ($name -ne "") {
                            $names += $name
                            continue
                        }
                    }
                    
                    # Essayer SerialNumberID
                    if ($monitor.SerialNumberID) {
                        $name = Convert-EDIDToString $monitor.SerialNumberID
                        if ($name -ne "" -and $name.Length -gt 3) {
                            $names += $name
                            continue
                        }
                    }
                }
                
                $names
                '''
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
                print(f"Noms EDID détectés: {names}")
                return names
                
        except Exception as e:
            print(f"Erreur EDID: {e}")
        return []
    
    def detect_screens(self):
        """Détecte tous les écrans connectés"""
        try:
            # Utiliser screeninfo en priorité pour obtenir la résolution native correcte
            print("Détection des écrans avec screeninfo...")
            self.screens = screeninfo.get_monitors()
            
            # Afficher les informations de détection
            print(f"Écrans screeninfo détectés: {len(self.screens)}")
            for i, screen in enumerate(self.screens):
                print(f"Écran screeninfo {i+1}: {screen.width}x{screen.height} à ({screen.x}, {screen.y}) - {screen.name}")
            
            # Correction spéciale pour le moniteur Samsung
            # Le moniteur Samsung est à (1920, -527) et devrait être 3840x2160 (native)
            # mais screeninfo peut détecter 2560x1440 (scaled)
            for screen in self.screens:
                if screen.x == 1920 and screen.y == -527:
                    if screen.width == 2560 and screen.height == 1440:
                        print(f"Correction Samsung: {screen.width}x{screen.height} -> 3840x2160 (résolution native)")
                        screen.width = 3840
                        screen.height = 2160
            
            # Vérifier si screeninfo a détecté tous les écrans
            if len(self.screens) < 2:
                print("screeninfo n'a détecté qu'un écran, essai avec mss...")
                # Fallback vers mss si screeninfo ne détecte pas tous les écrans
                with mss.mss() as sct:
                    mss_monitors = sct.monitors
                    print(f"Moniteurs MSS détectés: {len(mss_monitors)}")
                    
                    # Créer des objets écran compatibles avec notre interface
                    self.screens = []
                    for i, monitor in enumerate(mss_monitors[1:], 1):  # Ignorer le moniteur 0 (virtuel)
                        # Inclure tous les écrans physiques (même avec coordonnées négatives)
                        # Les coordonnées négatives sont normales pour les écrans secondaires
                        screen = type('Monitor', (), {
                            'x': monitor['left'],
                            'y': monitor['top'],
                            'width': monitor['width'],
                            'height': monitor['height'],
                            'name': f'Écran {i}'
                        })()
                        self.screens.append(screen)
                        print(f"Écran MSS {i}: {screen.width}x{screen.height} à ({screen.x}, {screen.y})")
            
            print(f"Écrans détectés: {len(self.screens)}")
            
            # Charger les noms personnalisés sauvegardés
            custom_names = self.settings.get_custom_screen_names()
            print(f"Noms personnalisés chargés: {custom_names}")
            
            # Récupérer les noms des écrans (seulement si pas de noms personnalisés)
            screen_names = []
            if not custom_names:
                screen_names = self.get_screen_names()
                
                # Si pas de noms détectés, essayer la méthode EDID
                if not screen_names:
                    print("Tentative de détection EDID des noms d'écrans...")
                    screen_names = self.get_edid_names()
                
                # Si toujours pas de noms détectés, essayer une méthode alternative
                if not screen_names:
                    print("Tentative de détection alternative des noms d'écrans...")
                    screen_names = self.get_screen_names_alternative()
            
            # Associer intelligemment les noms aux écrans
            for i, screen in enumerate(self.screens):
                assigned_name = None
                
                # Créer une clé unique pour cet écran basée sur ses propriétés
                screen_key = f"{screen.width}x{screen.height}_{screen.x}_{screen.y}"
                
                # Vérifier d'abord s'il y a un nom personnalisé pour cet écran
                if screen_key in custom_names:
                    assigned_name = custom_names[screen_key]
                    print(f"Nom personnalisé trouvé pour l'écran {i+1}: {assigned_name}")
                
                # Si pas de nom personnalisé, utiliser la logique automatique
                elif screen_names:
                    # Méthode 1: Correspondance exacte par nom de marque et résolution
                    if screen.width == 1920 and screen.height == 1080:
                        # Écran Full HD - chercher BenQ en priorité
                        for name in screen_names:
                            if "BENQ" in name.upper():
                                assigned_name = name
                                break
                    
                    elif screen.width == 1280 and screen.height == 1024:
                        # Écran 4:3 - chercher Dell en priorité
                        for name in screen_names:
                            if "DELL" in name.upper():
                                assigned_name = name
                                break
                    
                    elif screen.width == 3840 and screen.height == 2160:
                        # Écran 4K - chercher Samsung en priorité
                        for name in screen_names:
                            if "SAMSUNG" in name.upper():
                                assigned_name = name
                                break
                    
                    elif screen.width == 2560 and screen.height == 1440:
                        # Écran 2K - chercher Samsung en priorité
                        for name in screen_names:
                            if "SAMSUNG" in name.upper():
                                assigned_name = name
                                break
                    
                    # Méthode 2: Si pas de correspondance exacte, utiliser l'ordre mais avec vérification
                    if not assigned_name:
                        # Essayer de faire correspondre par ordre de détection
                        if i < len(screen_names):
                            assigned_name = screen_names[i]
                        elif len(screen_names) > 0:
                            assigned_name = screen_names[0]
                    
                    # Méthode 3: Correspondance par position (écran principal = coordonnées 0,0)
                    if not assigned_name and screen.x == 0 and screen.y == 0:
                        # Écran principal - chercher BenQ ou Samsung
                        for name in screen_names:
                            if any(brand in name.upper() for brand in ["BENQ", "SAMSUNG"]):
                                assigned_name = name
                                break
                
                # Assigner le nom final
                if assigned_name:
                    screen.name = assigned_name
                    # Retirer ce nom de la liste pour éviter les doublons
                    if assigned_name in screen_names:
                        screen_names.remove(assigned_name)
                else:
                    # Nom par défaut basé sur la résolution
                    screen.name = f"{screen.width}x{screen.height}"
                
                print(f"Écran {i+1}: {screen.width}x{screen.height} à ({screen.x}, {screen.y}) - {screen.name}")
                
        except Exception as e:
            print(f"Erreur lors de la détection des écrans: {e}")
            # Fallback vers une détection basique
            self.screens = []
    
    def get_screen_names_alternative(self):
        """Méthode alternative pour récupérer les noms d'écrans"""
        try:
            # Utiliser une commande PowerShell différente pour les écrans connectés
            cmd = [
                'powershell', 
                '-Command', 
                '''
                # Récupérer les écrans actuellement connectés
                $connectedScreens = Get-WmiObject -Class Win32_DesktopMonitor | Where-Object {$_.Availability -eq 3}
                $names = @()
                
                foreach ($screen in $connectedScreens) {
                    if ($screen.Name -and $screen.Name -ne "Generic PnP Monitor") {
                        $names += $screen.Name
                    }
                }
                
                # Si pas de noms trouvés, essayer une autre méthode
                if ($names.Count -eq 0) {
                    $monitors = Get-WmiObject -Namespace root\\wmi -Class WmiMonitorID
                    foreach ($monitor in $monitors) {
                        $name = ""
                        foreach ($char in $monitor.UserFriendlyName) {
                            if ($char -ne 0) {
                                $name += [char]$char
                            }
                        }
                        if ($name.Trim() -ne "") {
                            $names += $name.Trim()
                        }
                    }
                }
                
                # Limiter au nombre d'écrans actuellement connectés
                $screenCount = (Get-WmiObject -Class Win32_VideoController | Where-Object {$_.CurrentHorizontalResolution -gt 0}).Count
                $names[0..($screenCount-1)]
                '''
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0 and result.stdout.strip():
                names = result.stdout.strip().split('\n')
                cleaned_names = []
                for name in names:
                    if name.strip() and name.strip() != "":
                        cleaned_names.append(name.strip())
                print(f"Noms d'écrans détectés (méthode alternative): {cleaned_names}")
                return cleaned_names
        except Exception as e:
            print(f"Erreur méthode alternative: {e}")
        return []
    
    def detect_windows(self):
        """Détecte toutes les fenêtres d'applications ouvertes"""
        try:
            self.windows = []
            
            # Classes de fenêtres système à ignorer (plus spécifiques)
            system_classes = {
                'Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'NotifyIconOverflowWindow',
                'WorkerW', 'Shell_AppWnd', 'Progman', 'Dwm', 'DwmWindow',
                'Windows.UI.Core.CoreWindow', 'ApplicationFrameWindow',
                'Shell_CharmWindow', 'ImmersiveLauncher', 'SearchPane',
                'CEF-OSC-WIDGET'  # Classe spécifique pour NVIDIA GeForce Overlay
            }
            
            # Mots-clés spécifiques à ignorer dans les titres de fenêtres
            ignored_keywords = [
                'Microsoft', 'Windows', 'Settings', 'Control Panel',
                'Task Manager', 'Device Manager', 'System Properties', 'System Information',
                'Event Viewer', 'Services', 'Registry Editor', 'Command Prompt',
                'PowerShell', 'Windows Terminal', 'Task Scheduler', 'Performance Monitor',
                'Resource Monitor', 'System Configuration', 'System Restore',
                'Windows Defender', 'Windows Security', 'Windows Update',
                'Programs and Features', 'Default Programs', 'Network and Sharing Center',
                'User Accounts', 'Administrative Tools', 'System Tools',
                'NVIDIA GeForce', 'NVIDIA Control Panel', 'NVIDIA Settings',
                'NVIDIA GeForce Experience', 'NVIDIA GeForce Overlay'
            ]
            
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if window_text and window_text.strip():
                        # Obtenir les dimensions de la fenêtre
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            
                            # Obtenir le nom de la classe pour identifier l'application
                            class_name = win32gui.GetClassName(hwnd)
                            
                            # Vérifier si le titre contient des mots-clés à ignorer
                            should_ignore = any(keyword.lower() in window_text.lower() for keyword in ignored_keywords)
                            
                            # Vérifier si la classe est dans la liste des classes système
                            is_system_class = class_name in system_classes
                            
                            # Vérifier si c'est une fenêtre NVIDIA (plus spécifique)
                            is_nvidia = any(nvidia_keyword.lower() in window_text.lower() or 
                                           nvidia_keyword.lower() in class_name.lower() 
                                           for nvidia_keyword in ['nvidia', 'geforce'])
                            
                            # Filtrer les fenêtres système et trop petites
                            if (width > 200 and height > 150 and 
                                not is_system_class and
                                not should_ignore and
                                not is_nvidia and
                                # Ignorer seulement la fenêtre principale de MultiScreenCapt-Clikdoo-v1.0, pas les autres fenêtres
                                not (window_text == 'MultiScreenCapt-Clikdoo-v1.0')):
                                
                                # Vérifier que la fenêtre a une zone client valide
                                try:
                                    client_rect = win32gui.GetClientRect(hwnd)
                                    client_width = client_rect[2] - client_rect[0]
                                    client_height = client_rect[3] - client_rect[1]
                                    
                                    # Ignorer les fenêtres avec une zone client trop petite
                                    if client_width > 100 and client_height > 100:
                                        # Vérifier que la fenêtre est vraiment visible et interactive
                                        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                                            # Créer un objet fenêtre
                                            window = type('Window', (), {
                                                'hwnd': hwnd,
                                                'title': window_text,
                                                'class_name': class_name,
                                                'width': width,
                                                'height': height,
                                                'left': rect[0],
                                                'top': rect[1],
                                                'right': rect[2],
                                                'bottom': rect[3]
                                            })()
                                            
                                            windows.append(window)
                                except:
                                    # Si on ne peut pas obtenir la zone client, ignorer la fenêtre
                                    pass
                        except Exception as e:
                            print(f"Erreur lors de l'analyse de la fenêtre {hwnd}: {e}")
                return True
            
            # Énumérer toutes les fenêtres
            win32gui.EnumWindows(enum_windows_callback, self.windows)
            
            # Méthode alternative pour détecter les fenêtres avec pywinauto
            try:
                desktop = Desktop(backend="uia")
                windows_uia = desktop.windows()
                
                for window_uia in windows_uia:
                    try:
                        # Obtenir les propriétés de la fenêtre
                        title = window_uia.window_text()
                        class_name = window_uia.class_name()
                        hwnd = window_uia.handle
                        
                        # Vérifier si la fenêtre est déjà dans notre liste
                        if not any(w.hwnd == hwnd for w in self.windows):
                            # Obtenir les dimensions
                            rect = window_uia.rectangle()
                            width = rect.width()
                            height = rect.height()
                            
                            # Vérifier si c'est une fenêtre valide
                            if (title and title.strip() and 
                                width > 200 and height > 150 and
                                not any(keyword.lower() in title.lower() for keyword in ignored_keywords) and
                                not any(nvidia_keyword.lower() in title.lower() or 
                                       nvidia_keyword.lower() in class_name.lower() 
                                       for nvidia_keyword in ['nvidia', 'geforce']) and
                                # Vérifier si la classe est dans la liste des classes système
                                class_name not in system_classes and
                                # Ignorer seulement la fenêtre principale de MultiScreenCapt-Clikdoo-v1.0, pas les autres fenêtres
                                not (title == 'MultiScreenCapt-Clikdoo-v1.0')):
                                
                                # Créer un objet fenêtre
                                window = type('Window', (), {
                                    'hwnd': hwnd,
                                    'title': title,
                                    'class_name': class_name,
                                    'width': width,
                                    'height': height,
                                    'left': rect.left,
                                    'top': rect.top,
                                    'right': rect.right,
                                    'bottom': rect.bottom
                                })()
                                
                                self.windows.append(window)
                                print(f"  - Ajouté via UIA: {title} ({width}x{height}) - Classe: {class_name}")
                    except Exception as e:
                        # Ignorer les fenêtres qui ne peuvent pas être analysées
                        continue
                        
            except Exception as e:
                print(f"Erreur lors de la détection UIA: {e}")
            
            # Trier par titre
            self.windows.sort(key=lambda w: w.title.lower())
            
            print(f"Fenêtres détectées: {len(self.windows)}")
            for window in self.windows:
                print(f"  - {window.title} ({window.width}x{window.height}) - Classe: {window.class_name}")
                
        except Exception as e:
            print(f"Erreur lors de la détection des fenêtres: {e}")
            self.windows = []
    
    def create_interface(self):
        """Crée l'interface utilisateur avec système d'onglets"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Changé pour accommoder le système d'onglets
        
        # Titre
        title_label = ttk.Label(main_frame, text=get_text(self.current_language, 'app_title'), font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Frame pour le sélecteur de langue
        language_frame = ttk.Frame(main_frame)
        language_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Label pour la langue
        language_label = ttk.Label(language_frame, text=get_text(self.current_language, 'language'))
        language_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        # Combobox pour sélectionner la langue
        self.language_var = tk.StringVar(value=self.current_language)
        language_combo = ttk.Combobox(language_frame, textvariable=self.language_var, 
                                     values=['en', 'fr', 'es'], state='readonly', width=10)
        language_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        # Labels pour les langues
        language_names = {
            'en': get_text(self.current_language, 'english'),
            'fr': get_text(self.current_language, 'french'),
            'es': get_text(self.current_language, 'spanish')
        }
        
        # Configurer l'affichage des langues
        language_combo['values'] = [language_names[lang] for lang in ['en', 'fr', 'es']]
        language_combo.set(language_names[self.current_language])
        
        # Fonction pour changer la langue
        def change_language(event):
            selected_text = language_combo.get()
            # Trouver la clé de langue correspondante
            for lang, name in language_names.items():
                if name == selected_text:
                    if lang != self.current_language:
                        self.current_language = lang
                        self.settings.set_language(lang)
                        self.refresh_interface()
                    break
        
        language_combo.bind('<<ComboboxSelected>>', change_language)
        
        # Frame pour les contrôles (dossier de sauvegarde)
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Bouton pour changer le dossier de sauvegarde
        self.save_path_var = tk.StringVar(value=self.save_directory)
        save_label = ttk.Label(controls_frame, text=get_text(self.current_language, 'save_directory_label'))
        save_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        save_entry = ttk.Entry(controls_frame, textvariable=self.save_path_var, width=50)
        save_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Bouton pour ouvrir la gestion des chemins sauvegardés
        manage_paths_button = ttk.Button(controls_frame, text=get_text(self.current_language, 'manage_paths_button'), command=self.browse_save_directory)
        manage_paths_button.grid(row=0, column=2)
        
        controls_frame.columnconfigure(1, weight=1)
        
        # Système d'onglets
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Onglet Écran
        self.screen_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.screen_tab, text=get_text(self.current_language, 'screen_tab'))
        
        # Onglet Fenêtre
        self.window_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.window_tab, text=get_text(self.current_language, 'window_tab'))
        
        # Créer le contenu de l'onglet Écran
        self.create_screen_tab()
        
        # Créer le contenu de l'onglet Fenêtre
        self.create_window_tab()
    
    def create_screen_tab(self):
        """Crée le contenu de l'onglet Écran"""
        # Configuration du grid pour l'onglet Écran
        self.screen_tab.columnconfigure(0, weight=1)
        self.screen_tab.rowconfigure(1, weight=1)  # Changé de row 2 à row 1 pour la frame des écrans
        
        # Frame pour corriger les noms d'écrans
        names_frame = ttk.LabelFrame(self.screen_tab, text=get_text(self.current_language, 'correct_screen_names_label'), padding="5")
        names_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Bouton pour corriger les noms
        correct_names_button = ttk.Button(names_frame, text=get_text(self.current_language, 'correct_screen_names_button'), 
                                        command=self.correct_screen_names)
        correct_names_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Label d'information
        info_label = ttk.Label(names_frame, text=get_text(self.current_language, 'screen_name_correction_info'))
        info_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Frame pour les écrans
        screens_frame = ttk.LabelFrame(self.screen_tab, text=get_text(self.current_language, 'detected_screens_label'), padding="10")
        screens_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        screens_frame.columnconfigure(0, weight=1)
        screens_frame.rowconfigure(0, weight=1)
        
        # Canvas pour afficher les écrans
        self.canvas = tk.Canvas(screens_frame, bg="white", relief=tk.SUNKEN, bd=1)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar pour le canvas
        scrollbar = ttk.Scrollbar(screens_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame pour le contenu du canvas
        self.canvas_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.canvas_frame, anchor=tk.NW)
        
        # Afficher les écrans
        self.display_screens()
        
        # Configurer le redimensionnement du canvas
        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Configurer le scroll fluide pour tous les widgets
        self.setup_fluid_scrolling(self.canvas, self.canvas_frame)
    
    def create_window_tab(self):
        """Crée le contenu de l'onglet Fenêtre"""
        # Configuration du grid pour l'onglet Fenêtre
        self.window_tab.columnconfigure(0, weight=1)
        self.window_tab.rowconfigure(1, weight=1)  # Changé de row 2 à row 1 pour la frame des fenêtres
        
        # Frame pour les contrôles (bouton actualiser)
        controls_frame = ttk.Frame(self.window_tab)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Bouton pour actualiser les fenêtres
        refresh_button = ttk.Button(controls_frame, text=get_text(self.current_language, 'refresh_windows'), 
                                   command=self.refresh_windows)
        refresh_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Frame pour les fenêtres
        windows_frame = ttk.LabelFrame(self.window_tab, text=get_text(self.current_language, 'detected_windows'), padding="10")
        windows_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        windows_frame.columnconfigure(0, weight=1)
        windows_frame.rowconfigure(0, weight=1)
        
        # Canvas pour afficher les fenêtres
        self.window_canvas = tk.Canvas(windows_frame, bg="white", relief=tk.SUNKEN, bd=1)
        self.window_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar pour le canvas
        window_scrollbar = ttk.Scrollbar(windows_frame, orient=tk.VERTICAL, command=self.window_canvas.yview)
        window_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.window_canvas.configure(yscrollcommand=window_scrollbar.set)
        
        # Frame pour le contenu du canvas
        self.window_canvas_frame = ttk.Frame(self.window_canvas)
        self.window_canvas.create_window((0, 0), window=self.window_canvas_frame, anchor=tk.NW)
        
        # Afficher les fenêtres
        self.display_windows()
        
        # Configurer le redimensionnement du canvas
        self.window_canvas_frame.bind("<Configure>", lambda e: self.window_canvas.configure(scrollregion=self.window_canvas.bbox("all")))
        
        # Configurer le scroll fluide pour tous les widgets
        self.setup_fluid_scrolling(self.window_canvas, self.window_canvas_frame)
    
    def refresh_interface(self):
        """Rafraîchit l'interface avec la nouvelle langue"""
        # Sauvegarder l'onglet actuellement sélectionné
        current_tab = 0  # Par défaut, premier onglet
        if hasattr(self, 'notebook'):
            current_tab = self.notebook.index(self.notebook.select())
        
        # Mettre à jour le titre de la fenêtre
        self.root.title(get_text(self.current_language, 'app_title'))
        
        # Recréer complètement l'interface
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.create_interface()
        
        # Redétecter les fenêtres après la recréation de l'interface
        self.detect_windows()
        
        # Mettre à jour les textes des onglets
        if hasattr(self, 'notebook'):
            self.notebook.tab(0, text=get_text(self.current_language, 'screen_tab'))
            self.notebook.tab(1, text=get_text(self.current_language, 'window_tab'))
            
            # Restaurer l'onglet précédemment sélectionné
            self.notebook.select(current_tab)
    
    def setup_fluid_scrolling(self, canvas, content_frame):
        """Configure un scroll fluide et uniforme pour tous les widgets"""
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Lier directement au canvas et au content_frame
        canvas.bind("<MouseWheel>", on_mousewheel)
        content_frame.bind("<MouseWheel>", on_mousewheel)
        
        # Fonction pour lier le scroll à tous les widgets enfants
        def bind_to_children(parent):
            for child in parent.winfo_children():
                # Éviter de lier plusieurs fois le même événement
                child.bind("<MouseWheel>", on_mousewheel)
                bind_to_children(child)
        
        # Appliquer immédiatement aux widgets existants
        bind_to_children(content_frame)
        
        # Fonction pour rebinder après ajout de nouveaux widgets
        def rebind_after_update():
            bind_to_children(content_frame)
        
        # Stocker la fonction pour pouvoir l'appeler plus tard
        content_frame.rebind_scroll = rebind_after_update
    
    def display_screens(self):
        """Affiche les écrans détectés dans l'interface"""
        # Calculer l'échelle pour afficher les écrans
        max_width = 200
        max_height = 150
        
        for i, screen in enumerate(self.screens):
            # Calculer les dimensions réduites
            scale = min(max_width / screen.width, max_height / screen.height)
            display_width = int(screen.width * scale)
            display_height = int(screen.height * scale)
            
            # Frame pour chaque écran
            screen_frame = ttk.Frame(self.canvas_frame, relief=tk.RAISED, borderwidth=2)
            screen_frame.grid(row=i, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
            
            # Ajouter une référence à l'écran pour le feedback visuel
            screen_frame.screen_info = screen
            
            # Canvas pour l'aperçu de l'écran
            preview_canvas = tk.Canvas(screen_frame, width=display_width, height=display_height, 
                                     bg="lightgray", relief=tk.SUNKEN, bd=1)
            preview_canvas.grid(row=0, column=0, padx=5, pady=5)
            
            # Dessiner un aperçu simple de l'écran
            preview_canvas.create_rectangle(2, 2, display_width-2, display_height-2, 
                                          outline="black", width=1)
            
            # Ajouter des détails pour simuler un écran
            preview_canvas.create_text(display_width//2, display_height//2, 
                                     text=f"{screen.width}×{screen.height}", 
                                     font=("Arial", 10))
            
            # Informations sur l'écran
            info_frame = ttk.Frame(screen_frame)
            info_frame.grid(row=0, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
            
            # Nom de l'écran (essayer de récupérer le nom réel)
            screen_name = getattr(screen, 'name', f'Écran {i+1}')
            if screen_name == 'Nom inconnu' or not screen_name:
                screen_name = f'Écran {i+1}'
            name_label = ttk.Label(info_frame, text=screen_name, font=("Arial", 12, "bold"))
            name_label.grid(row=0, column=0, sticky=tk.W)
            
            # Dimensions
            dim_label = ttk.Label(info_frame, text=f"{get_text(self.current_language, 'resolution')}: {screen.width} × {screen.height}")
            dim_label.grid(row=1, column=0, sticky=tk.W)
            
            # Position
            pos_label = ttk.Label(info_frame, text=f"{get_text(self.current_language, 'position')}: ({screen.x}, {screen.y})")
            pos_label.grid(row=2, column=0, sticky=tk.W)
            
            # Bouton de capture
            capture_button = ttk.Button(info_frame, text=get_text(self.current_language, 'capture_button'), 
                                      command=lambda s=screen: self.capture_screen(s))
            capture_button.grid(row=3, column=0, pady=(10, 0), sticky=tk.W)
            
            # Lier le clic sur le canvas à la capture
            preview_canvas.bind("<Button-1>", lambda e, s=screen: self.capture_screen(s))
            
            # Configurer le grid
            screen_frame.columnconfigure(1, weight=1)
        
        # Rebinder le scroll après la création des widgets
        if hasattr(self.canvas_frame, 'rebind_scroll'):
            self.canvas_frame.rebind_scroll()
    
    def format_window_name(self, title):
        """Formate le nom de la fenêtre pour mettre l'application en premier"""
        # Cas spécial pour Steam (titre simple)
        if title == "Steam":
            return "Steam"
        
        # Cas spécial pour les titres avec plusieurs tirets (comme "Cursor - main.py - MultiScreenCapt-Clikdoo-v1.0")
        if title.count(' - ') >= 2:
            parts = title.split(' - ')
            if len(parts) >= 3:
                # Prendre le premier élément comme nom d'app
                app_name = parts[0].strip()
                # Le reste comme description
                rest = ' - '.join(parts[1:]).strip()
                
                # Nettoyer l'app name
                clean_app_name = app_name
                while clean_app_name and clean_app_name[0] in '([{':
                    clean_app_name = clean_app_name[1:]
                while clean_app_name and clean_app_name[-1] in ')]}':
                    clean_app_name = clean_app_name[:-1]
                clean_app_name = clean_app_name.strip()
                
                if (clean_app_name and 
                    len(clean_app_name) <= 30 and
                    len(clean_app_name) >= 2):
                    return f"{clean_app_name} - {rest}..."
        
        # Cas spécial pour les titres avec des parenthèses au début (comme Chrome)
        if title.startswith('(') and ' - ' in title:
            parts = title.split(' - ', 1)
            if len(parts) == 2:
                # Extraire le nom de l'app après les parenthèses
                app_part = parts[0].strip()
                rest_part = parts[1].strip()
                
                # Chercher le nom de l'app dans la deuxième partie
                if ' - ' in rest_part:
                    app_name, final_rest = rest_part.split(' - ', 1)
                    if app_name and len(app_name) <= 30:
                        return f"{app_name} - {final_rest}"
        
        # Séparateurs communs dans les titres de fenêtres
        separators = [' - ', ' | ', ' : ', '...', ' – ', ' — ']
        
        # Chercher le premier séparateur
        for sep in separators:
            if sep in title:
                parts = title.split(sep, 1)  # Split seulement sur la première occurrence
                if len(parts) == 2:
                    app_name = parts[0].strip()
                    rest = parts[1].strip()
                    
                    # Si l'app name est vide ou trop courte, garder l'original
                    if len(app_name) < 2:
                        continue
                    
                    # Nettoyer l'app name des caractères spéciaux au début
                    clean_app_name = app_name
                    while clean_app_name and clean_app_name[0] in '([{':
                        clean_app_name = clean_app_name[1:]
                    while clean_app_name and clean_app_name[-1] in ')]}':
                        clean_app_name = clean_app_name[:-1]
                    clean_app_name = clean_app_name.strip()
                    
                    # Vérifier si l'app name ressemble à un nom d'application
                    if (clean_app_name and 
                        len(clean_app_name) <= 30 and
                        len(clean_app_name) >= 2):
                        return f"{clean_app_name} - {rest}..."
        
        # Si aucun séparateur trouvé ou format non reconnu, garder l'original
        return title

    def display_windows(self):
        """Affiche les fenêtres détectées dans l'interface"""
        # Nettoyer le canvas
        for widget in self.window_canvas_frame.winfo_children():
            widget.destroy()
        
        if not self.windows:
            # Afficher un message si aucune fenêtre n'est trouvée
            no_windows_label = ttk.Label(self.window_canvas_frame, 
                                       text=get_text(self.current_language, 'no_windows_found'),
                                       font=("Arial", 12))
            no_windows_label.grid(row=0, column=0, padx=20, pady=20)
            return
        
        # Calculer l'échelle pour afficher les fenêtres
        max_width = 200
        max_height = 150
        
        for i, window in enumerate(self.windows):
            # Obtenir les dimensions de la zone client pour l'affichage
            try:
                client_rect = win32gui.GetClientRect(window.hwnd)
                client_width = client_rect[2] - client_rect[0]
                client_height = client_rect[3] - client_rect[1]
            except:
                # Fallback aux dimensions de la fenêtre entière
                client_width = window.width
                client_height = window.height
            
            # Calculer les dimensions réduites pour l'affichage
            scale = min(max_width / window.width, max_height / window.height)
            display_width = int(window.width * scale)
            display_height = int(window.height * scale)
            
            # Frame pour chaque fenêtre
            window_frame = ttk.Frame(self.window_canvas_frame, relief=tk.RAISED, borderwidth=2)
            window_frame.grid(row=i, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
            
            # Ajouter une référence à la fenêtre pour le feedback visuel
            window_frame.window_info = window
            
            # Canvas pour l'aperçu de la fenêtre
            preview_canvas = tk.Canvas(window_frame, width=display_width, height=display_height, 
                                     bg="lightblue", relief=tk.SUNKEN, bd=1)
            preview_canvas.grid(row=0, column=0, padx=5, pady=5)
            
            # Dessiner un aperçu de la fenêtre avec bordure et zone client
            preview_canvas.create_rectangle(2, 2, display_width-2, display_height-2, 
                                          outline="black", width=2, fill="lightgray")
            
            # Dessiner la zone client (zone de capture) - plus précise
            try:
                # Calculer la position relative de la zone client
                client_scale_x = (display_width - 10) / window.width
                client_scale_y = (display_height - 10) / window.height
                
                # Calculer les marges (bordures + titre)
                margin_left = (window.width - client_width) / 2
                margin_top = (window.height - client_height) / 2
                
                # Position de la zone client dans l'aperçu
                client_x = 5 + int(margin_left * client_scale_x)
                client_y = 5 + int(margin_top * client_scale_y)
                client_display_width = int(client_width * client_scale_x)
                client_display_height = int(client_height * client_scale_y)
                
                # S'assurer que les dimensions sont positives
                if client_display_width > 0 and client_display_height > 0:
                    preview_canvas.create_rectangle(client_x, client_y, 
                                                  client_x + client_display_width, client_y + client_display_height,
                                                  outline="blue", width=2, fill="white")
                    
                    # Ajouter un indicateur visuel pour la zone de capture
                    preview_canvas.create_text(display_width//2, display_height//2, 
                                             text=f"{client_width}×{client_height}", 
                                             font=("Arial", 9), fill="blue")
                else:
                    # Fallback si le calcul échoue
                    preview_canvas.create_rectangle(5, 5, display_width-5, display_height-5,
                                                  outline="blue", width=2, fill="white")
                    preview_canvas.create_text(display_width//2, display_height//2, 
                                             text=f"{client_width}×{client_height}", 
                                             font=("Arial", 9))
            except:
                # Fallback en cas d'erreur
                preview_canvas.create_rectangle(5, 5, display_width-5, display_height-5,
                                              outline="blue", width=2, fill="white")
                preview_canvas.create_text(display_width//2, display_height//2, 
                                         text=f"{client_width}×{client_height}", 
                                         font=("Arial", 9))
            
            # Informations sur la fenêtre
            info_frame = ttk.Frame(window_frame)
            info_frame.grid(row=0, column=1, padx=10, pady=5, sticky=(tk.W, tk.E))
            
            # Nom de la fenêtre reformaté pour mettre l'app en premier
            formatted_title = self.format_window_name(window.title)
            display_title = formatted_title
            if len(display_title) > 40:
                display_title = display_title[:37] + "..."
            
            name_label = ttk.Label(info_frame, text=display_title, font=("Arial", 12, "bold"))
            name_label.grid(row=0, column=0, sticky=tk.W)
            
            # Dimensions de la zone client (zone de capture)
            dim_label = ttk.Label(info_frame, text=f"{get_text(self.current_language, 'window_size')}: {client_width} × {client_height}")
            dim_label.grid(row=1, column=0, sticky=tk.W)
            
            # Classe de la fenêtre (pour debug) - masquée par défaut
            # class_label = ttk.Label(info_frame, text=f"Class: {window.class_name}", font=("Arial", 8))
            # class_label.grid(row=2, column=0, sticky=tk.W)
            
            # Bouton de capture
            capture_button = ttk.Button(info_frame, text=get_text(self.current_language, 'capture_this_window'), 
                                      command=lambda w=window: self.capture_window(w))
            capture_button.grid(row=2, column=0, pady=(10, 0), sticky=tk.W)
            
            # Lier le clic sur le canvas à la capture
            preview_canvas.bind("<Button-1>", lambda e, w=window: self.capture_window(w))
            
            # Configurer le grid
            window_frame.columnconfigure(1, weight=1)
        
        # Rebinder le scroll après la création des widgets
        if hasattr(self.window_canvas_frame, 'rebind_scroll'):
            self.window_canvas_frame.rebind_scroll()
    
    def refresh_windows(self):
        """Actualise la liste des fenêtres détectées"""
        # Appeler le débogage pour voir toutes les fenêtres
        self.debug_windows()
        
        self.detect_windows()
        self.display_windows()
    
    def debug_windows(self):
        """Méthode de débogage pour afficher toutes les fenêtres détectées"""
        print("\n=== DÉBOGAGE DÉTECTION FENÊTRES ===")
        try:
            all_windows = []
            
            def enum_all_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if window_text and window_text.strip():
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            class_name = win32gui.GetClassName(hwnd)
                            
                            if width > 100 and height > 100:  # Critères plus larges pour le débogage
                                windows.append({
                                    'hwnd': hwnd,
                                    'title': window_text,
                                    'class_name': class_name,
                                    'width': width,
                                    'height': height
                                })
                        except:
                            pass
                return True
            
            win32gui.EnumWindows(enum_all_windows_callback, all_windows)
            
            print(f"Toutes les fenêtres visibles ({len(all_windows)}):")
            for window in sorted(all_windows, key=lambda w: w['title'].lower()):
                print(f"  - {window['title']} ({window['width']}x{window['height']}) - Classe: {window['class_name']}")
                
        except Exception as e:
            print(f"Erreur lors du débogage: {e}")
        print("=== FIN DÉBOGAGE ===\n")
    


    def browse_save_directory(self):
        """Ouvre un dialogue pour choisir le dossier de sauvegarde"""
        print("DEBUG: Début de browse_save_directory")
        try:
            print(f"DEBUG: save_directory actuel: {self.save_directory}")
            
            # Créer une fenêtre de dialogue personnalisée
            dialog = tk.Toplevel(self.root)
            dialog.title("Sélectionner un dossier de sauvegarde")
            dialog.geometry("700x500")  # Réduit car on a supprimé l'arborescence
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Centrer la fenêtre
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
            y = (dialog.winfo_screenheight() // 2) - (500 // 2)
            dialog.geometry(f"700x500+{x}+{y}")
            
            # Frame principal
            main_frame = tk.Frame(dialog, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Label d'instruction
            label = tk.Label(main_frame, text="Sélectionnez le dossier de sauvegarde:", font=("Arial", 12, "bold"))
            label.pack(pady=(0, 20))
            
            # Frame pour le chemin actuel
            path_frame = tk.Frame(main_frame)
            path_frame.pack(fill=tk.X, pady=(0, 20))
            
            path_label = tk.Label(path_frame, text="Chemin actuel:", font=("Arial", 10))
            path_label.pack(anchor=tk.W)
            
            # Variable pour le chemin sélectionné
            selected_path = tk.StringVar(value=self.save_directory)
            
            # Entry pour afficher/modifier le chemin (copiable)
            path_entry = tk.Entry(path_frame, textvariable=selected_path, font=("Arial", 10))
            path_entry.pack(fill=tk.X, pady=(5, 0))
            
            # Frame pour le bouton Ajout
            add_frame = tk.Frame(path_frame)
            add_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Charger les chemins sauvegardés depuis les paramètres
            saved_paths = self.settings.get_saved_paths()
            
            def add_current_path():
                """Ajoute le chemin actuel à la liste des chemins sauvegardés"""
                current_path = selected_path.get()
                if current_path and os.path.exists(current_path):
                    if current_path not in saved_paths:
                        saved_paths.append(current_path)
                        self.settings.save_paths(saved_paths)
                        update_saved_paths_display()
                    # Pas de notification - l'ajout est silencieux
                # Pas de notification d'erreur - l'action est silencieuse
            
            add_btn = tk.Button(add_frame, text="Ajout", command=add_current_path, 
                              bg="#FF9800", fg="white", font=("Arial", 10, "bold"), width=10)
            add_btn.pack(side=tk.LEFT)
            
            # Frame pour les chemins sauvegardés
            saved_paths_frame = tk.Frame(main_frame)
            saved_paths_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
            
            saved_paths_label = tk.Label(saved_paths_frame, text="Chemins sauvegardés:", font=("Arial", 10, "bold"))
            saved_paths_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Zone blanche pour afficher les chemins sauvegardés
            saved_paths_canvas = tk.Canvas(saved_paths_frame, bg="white", height=150)
            saved_paths_canvas.pack(fill=tk.BOTH, expand=True)
            
            saved_paths_scrollbar = ttk.Scrollbar(saved_paths_frame, orient=tk.VERTICAL, command=saved_paths_canvas.yview)
            saved_paths_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            saved_paths_canvas.configure(yscrollcommand=saved_paths_scrollbar.set)
            
            # Frame pour le contenu des chemins sauvegardés
            saved_paths_content = tk.Frame(saved_paths_canvas, bg="white")
            saved_paths_canvas.create_window((0, 0), window=saved_paths_content, anchor="nw")
            
            def update_saved_paths_display():
                """Met à jour l'affichage des chemins sauvegardés"""
                # Supprimer tous les widgets existants
                for widget in saved_paths_content.winfo_children():
                    widget.destroy()
                
                if not saved_paths:
                    no_paths_label = tk.Label(saved_paths_content, text="Aucun chemin sauvegardé", 
                                            fg="gray", bg="white", font=("Arial", 10, "italic"))
                    no_paths_label.pack(pady=20)
                else:
                    for i, path in enumerate(saved_paths):
                        path_frame_item = tk.Frame(saved_paths_content, bg="white")
                        path_frame_item.pack(fill=tk.X, pady=2)
                        
                        # Bouton pour sélectionner le chemin
                        select_path_btn = tk.Button(path_frame_item, text=f"📁 {path}", 
                                                  command=lambda p=path: select_saved_path(p),
                                                  bg="white", fg="blue", font=("Arial", 9),
                                                  relief=tk.FLAT, anchor=tk.W, justify=tk.LEFT)
                        select_path_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                        
                        # Bouton pour supprimer le chemin
                        delete_btn = tk.Button(path_frame_item, text="❌", 
                                             command=lambda p=path: delete_saved_path(p),
                                             bg="white", fg="red", font=("Arial", 8),
                                             relief=tk.FLAT, width=3)
                        delete_btn.pack(side=tk.RIGHT)
                
                # Mettre à jour la zone de défilement
                saved_paths_content.update_idletasks()
                saved_paths_canvas.configure(scrollregion=saved_paths_canvas.bbox("all"))
            
            def select_saved_path(path):
                """Sélectionne un chemin sauvegardé"""
                if os.path.exists(path):
                    selected_path.set(path)
                    # Pas de notification - la sélection est silencieuse
                else:
                    # Supprimer le chemin invalide silencieusement
                    if path in saved_paths:
                        saved_paths.remove(path)
                        self.settings.save_paths(saved_paths)
                        update_saved_paths_display()
            
            def delete_saved_path(path):
                """Supprime un chemin sauvegardé"""
                if path in saved_paths:
                    saved_paths.remove(path)
                    self.settings.save_paths(saved_paths)
                    update_saved_paths_display()
                    # Pas de notification - la suppression est silencieuse
            
            # Afficher les chemins sauvegardés
            update_saved_paths_display()
            
            # Frame pour les boutons
            button_frame = tk.Frame(main_frame)
            button_frame.pack(side=tk.BOTTOM, pady=(20, 0))
            
            def select_current():
                """Sélectionne le dossier actuellement affiché"""
                path = selected_path.get()
                if path and os.path.exists(path):
                    self.save_directory = path
                    self.save_path_var.set(path)
                    self.settings.set_save_directory(path)
                    print(f"DEBUG: Dossier sélectionné: {path}")
                    dialog.destroy()
                # Pas de notification d'erreur - l'action est silencieuse
            
            def cancel():
                """Annule la sélection"""
                dialog.destroy()
            
            # Boutons
            select_btn = tk.Button(button_frame, text="Sélectionner ce dossier", command=select_current, 
                                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=20)
            select_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            cancel_btn = tk.Button(button_frame, text="Annuler", command=cancel, 
                                 bg="#f44336", fg="white", font=("Arial", 10), width=15)
            cancel_btn.pack(side=tk.LEFT)
            
            # Attendre que la fenêtre soit fermée
            dialog.wait_window()
            
            print("DEBUG: Dialogue fermé")
            
        except Exception as e:
            print(f"DEBUG: Exception dans browse_save_directory: {e}")
            print(f"DEBUG: Type d'exception: {type(e)}")
            import traceback
            traceback.print_exc()
            # Pas de notification d'erreur - l'erreur est silencieuse
        print("DEBUG: Fin de browse_save_directory")
    
    def correct_screen_names(self):
        """Permet à l'utilisateur de corriger les noms d'écrans"""
        # Créer une fenêtre de dialogue
        dialog = tk.Toplevel(self.root)
        dialog.title(get_text(self.current_language, 'correct_screen_names_dialog_title'))
        dialog.geometry("500x350")  # Augmenté la hauteur pour le nouveau bouton
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = ttk.Label(main_frame, text=get_text(self.current_language, 'correct_screen_names_dialog_title'), font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        instructions = ttk.Label(main_frame, text=get_text(self.current_language, 'correct_screen_names_dialog_instructions'))
        instructions.pack(pady=(0, 10))
        
        # Variables pour les noms
        name_vars = []
        entries = []
        
        # Créer les champs pour chaque écran
        for i, screen in enumerate(self.screens):
            frame = ttk.Frame(main_frame)
            frame.pack(fill=tk.X, pady=5)
            
            # Label avec les informations de l'écran
            info_text = f"{get_text(self.current_language, 'screen')} {i+1} ({screen.width}x{screen.height}) :"
            label = ttk.Label(frame, text=info_text, width=20)
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Champ de saisie
            var = tk.StringVar(value=screen.name)
            name_vars.append(var)
            entry = ttk.Entry(frame, textvariable=var, width=30)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries.append(entry)
        
        # Boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def apply_names():
            # Appliquer les nouveaux noms
            custom_names = {}
            for i, (screen, var) in enumerate(zip(self.screens, name_vars)):
                new_name = var.get().strip()
                if new_name:  # Ne sauvegarder que si le nom n'est pas vide
                    screen.name = new_name
                    # Créer une clé unique pour cet écran
                    screen_key = f"{screen.width}x{screen.height}_{screen.x}_{screen.y}"
                    custom_names[screen_key] = new_name
                    print(f"Nom corrigé pour l'écran {i+1}: {screen.name}")
            
            # Sauvegarder les noms personnalisés
            self.settings.set_custom_screen_names(custom_names)
            
            # Fermer la fenêtre
            dialog.destroy()
            
            # Rafraîchir l'affichage
            self.refresh_display()
            
            messagebox.showinfo(get_text(self.current_language, 'success_message'), get_text(self.current_language, 'screen_name_correction_success'))
        
        def reset_names():
            # Demander confirmation
            result = messagebox.askyesno(
                get_text(self.current_language, 'reset_names_confirm_title'),
                get_text(self.current_language, 'reset_names_confirm_message')
            )
            
            if result:
                # Réinitialiser les noms personnalisés
                self.settings.reset_custom_screen_names()
                
                # Redétecter les écrans avec les noms par défaut
                self.detect_screens()
                
                # Fermer la fenêtre
                dialog.destroy()
                
                # Rafraîchir l'affichage
                self.refresh_display()
                
                messagebox.showinfo(get_text(self.current_language, 'success_message'), get_text(self.current_language, 'reset_names_success'))
        
        def cancel():
            dialog.destroy()
        
        # Boutons
        apply_button = ttk.Button(button_frame, text=get_text(self.current_language, 'apply_button'), command=apply_names)
        apply_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        reset_button = ttk.Button(button_frame, text=get_text(self.current_language, 'reset_names_button'), command=reset_names)
        reset_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_button = ttk.Button(button_frame, text=get_text(self.current_language, 'cancel_button'), command=cancel)
        cancel_button.pack(side=tk.RIGHT)
        
        # Focus sur le premier champ
        if entries:
            entries[0].focus()
    
    def refresh_display(self):
        """Rafraîchit l'affichage des écrans"""
        # Supprimer tous les widgets du canvas_frame
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        
        # Réafficher les écrans
        self.display_screens()
        
        # Mettre à jour le canvas
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def get_monitor_dpi_scaling(self, screen):
        """Get DPI scaling for a specific monitor"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Debug: Print screen info
            print(f"DEBUG: Checking screen {screen.name}: x={screen.x}, y={screen.y}, width={screen.width}, height={screen.height}")
            
            # Special handling for Samsung monitor based on coordinates
            # The Samsung monitor is at (1920, -527) with size 3840x2160 (native)
            if (screen.x == 1920 and screen.y == -527 and 
                screen.width == 3840 and screen.height == 2160):
                print(f"Screen {screen.name}: Detected as Samsung monitor")
                
                # Try to get the monitor handle for this specific screen
                center_x = screen.x + screen.width // 2
                center_y = screen.y + screen.height // 2
                
                # Get the monitor handle for this point
                monitor_handle = ctypes.windll.user32.MonitorFromPoint(
                    wintypes.POINT(center_x, center_y), 
                    2  # MONITOR_DEFAULTTONEAREST
                )
                
                print(f"Samsung monitor handle: {monitor_handle}")
                
                dpi_x = wintypes.UINT()
                dpi_y = wintypes.UINT()
                
                result = ctypes.windll.shcore.GetDpiForMonitor(monitor_handle, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                
                if result == 0:  # S_OK
                    scaling_x = dpi_x.value / 96.0
                    scaling_y = dpi_y.value / 96.0
                    print(f"Screen {screen.name}: DPI=({dpi_x.value}, {dpi_y.value}) -> Scaling=({scaling_x:.2f}, {scaling_y:.2f})")
                    return scaling_x, scaling_y
                else:
                    print(f"GetDpiForMonitor failed for Samsung: {result}")
                    # For Samsung, we know it should be 150% scaling
                    print(f"Screen {screen.name}: Using known Samsung scaling (1.50, 1.50)")
                    return 1.5, 1.5
            else:
                print(f"DEBUG: Screen {screen.name} does not match Samsung criteria")
                # For other monitors, use the standard approach
                center_x = screen.x + screen.width // 2
                center_y = screen.y + screen.height // 2
                
                monitor_handle = ctypes.windll.user32.MonitorFromPoint(
                    wintypes.POINT(center_x, center_y), 
                    2  # MONITOR_DEFAULTTONEAREST
                )
                
                dpi_x = wintypes.UINT()
                dpi_y = wintypes.UINT()
                
                result = ctypes.windll.shcore.GetDpiForMonitor(monitor_handle, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                
                if result == 0:  # S_OK
                    scaling_x = dpi_x.value / 96.0
                    scaling_y = dpi_y.value / 96.0
                    print(f"Screen {screen.name}: DPI=({dpi_x.value}, {dpi_y.value}) -> Scaling=({scaling_x:.2f}, {scaling_y:.2f})")
                    return scaling_x, scaling_y
                else:
                    print(f"GetDpiForMonitor failed: {result}")
                    # Fallback to primary monitor
                    primary_monitor = ctypes.windll.user32.MonitorFromWindow(None, 2)
                    result = ctypes.windll.shcore.GetDpiForMonitor(primary_monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                    if result == 0:
                        scaling_x = dpi_x.value / 96.0
                        scaling_y = dpi_y.value / 96.0
                        print(f"Screen {screen.name}: Using primary monitor DPI=({dpi_x.value}, {dpi_y.value}) -> Scaling=({scaling_x:.2f}, {scaling_y:.2f})")
                        return scaling_x, scaling_y
                    else:
                        print(f"Primary monitor GetDpiForMonitor also failed: {result}")
                        return 1.0, 1.0
                
        except Exception as e:
            print(f"Error getting monitor DPI scaling: {e}")
            return 1.0, 1.0

    def capture_screen(self, screen):
        """Capture un écran spécifique"""
        try:
            print(f"Capture de l'écran: {screen.width}x{screen.height} à ({screen.x}, {screen.y})")
            
            # Get DPI scaling for this monitor
            scaling_x, scaling_y = self.get_monitor_dpi_scaling(screen)
            print(f"Using DPI scaling: ({scaling_x:.2f}, {scaling_y:.2f})")
            
            # Utiliser mss pour une capture directe et fiable
            with mss.mss() as sct:
                # Apply DPI scaling to coordinates if needed
                # Note: MSS might already handle DPI scaling, so we'll test both approaches
                monitor = {
                    "top": screen.y,
                    "left": screen.x,
                    "width": screen.width,
                    "height": screen.height
                }
                
                print(f"Capture directe avec coordonnées exactes: {monitor}")
                
                # Capturer l'écran avec mss
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Vérifier la qualité de l'image
                pixels = list(img.getdata())
                black_pixels = sum(1 for pixel in pixels if pixel == (0, 0, 0))
                total_pixels = len(pixels)
                black_percentage = (black_pixels / total_pixels) * 100
                
                print(f"Taille image: {img.size}")
                print(f"Pixels noirs: {black_pixels}/{total_pixels} ({black_percentage:.1f}%)")
                
                # If the image seems too small for the expected resolution, try with scaled coordinates
                expected_width = int(screen.width * scaling_x)
                expected_height = int(screen.height * scaling_y)
                
                if img.size != (expected_width, expected_height) and (scaling_x != 1.0 or scaling_y != 1.0):
                    print(f"Image size mismatch. Expected: ({expected_width}, {expected_height}), Got: {img.size}")
                    print("Trying with scaled coordinates...")
                    
                    # Try with scaled coordinates
                    scaled_monitor = {
                        "top": int(screen.y * scaling_y),
                        "left": int(screen.x * scaling_x),
                        "width": int(screen.width * scaling_x),
                        "height": int(screen.height * scaling_y)
                    }
                    
                    screenshot_scaled = sct.grab(scaled_monitor)
                    img_scaled = Image.frombytes("RGB", screenshot_scaled.size, screenshot_scaled.bgra, "raw", "BGRX")
                    
                    print(f"Scaled capture size: {img_scaled.size}")
                    
                    # Use the scaled image if it's larger
                    if img_scaled.size[0] * img_scaled.size[1] > img.size[0] * img.size[1]:
                        img = img_scaled
                        print("Using scaled capture")
            
            # Générer le nom de fichier avec timestamp et nom d'écran
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            screen_name = getattr(screen, 'name', f'Ecran_{screen.width}x{screen.height}')
            # Nettoyer le nom d'écran pour le nom de fichier
            safe_name = "".join(c for c in screen_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"MultiScreenCapt-Clikdoo_{safe_name}_{timestamp}.png"
            filepath = os.path.join(self.save_directory, filename)
            
            # Sauvegarder l'image
            img.save(filepath, "PNG")
            
            print(f"Capture sauvegardée: {filepath}")
            
            # Feedback visuel : changer temporairement le texte du bouton
            self.show_capture_feedback(screen)
            
        except Exception as e:
            print(f"Erreur lors de la capture: {e}")
            # Feedback visuel d'erreur
            self.show_capture_error(screen)
    
    def get_screen_bounds(self):
        """Retourne les limites de tous les écrans connectés"""
        bounds = []
        try:
            # Utiliser les mêmes écrans que ceux détectés par screeninfo
            # pour assurer la cohérence avec la détection des fenêtres
            for screen in self.screens:
                bounds.append({
                    'left': screen.x,
                    'top': screen.y,
                    'right': screen.x + screen.width,
                    'bottom': screen.y + screen.height,
                    'width': screen.width,
                    'height': screen.height
                })
                print(f"Écran ajouté aux limites: ({screen.x}, {screen.y}) {screen.width}x{screen.height}")
        except Exception as e:
            print(f"Erreur lors de la détection des limites d'écran: {e}")
            # Fallback avec mss si nécessaire
            try:
                with mss.mss() as sct:
                    for i, monitor in enumerate(sct.monitors[1:], 1):
                        bounds.append({
                            'left': monitor['left'],
                            'top': monitor['top'],
                            'right': monitor['left'] + monitor['width'],
                            'bottom': monitor['top'] + monitor['height'],
                            'width': monitor['width'],
                            'height': monitor['height']
                        })
            except Exception as mss_error:
                print(f"Erreur fallback MSS: {mss_error}")
        return bounds


    def clip_to_screen_bounds(self, capture_area):
        """Limite une zone de capture aux limites des écrans visibles"""
        left = capture_area['left']
        top = capture_area['top']
        width = capture_area['width']
        height = capture_area['height']
        
        # Obtenir les limites des écrans
        screen_bounds = self.get_screen_bounds()
        if not screen_bounds:
            return None
        
        # Trouver l'écran qui contient le plus de la zone demandée
        best_screen = None
        max_overlap = 0
        
        for screen in screen_bounds:
            # Calculer l'intersection
            screen_left = screen['left']
            screen_top = screen['top']
            screen_right = screen['right']
            screen_bottom = screen['bottom']
            
            # Intersection
            intersect_left = max(left, screen_left)
            intersect_top = max(top, screen_top)
            intersect_right = min(left + width, screen_right)
            intersect_bottom = min(top + height, screen_bottom)
            
            if intersect_left < intersect_right and intersect_top < intersect_bottom:
                overlap = (intersect_right - intersect_left) * (intersect_bottom - intersect_top)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_screen = screen
        
        if not best_screen:
            return None
        
        # Clipper aux limites de l'écran
        clipped_left = max(left, best_screen['left'])
        clipped_top = max(top, best_screen['top'])
        clipped_right = min(left + width, best_screen['right'])
        clipped_bottom = min(top + height, best_screen['bottom'])
        
        clipped_width = clipped_right - clipped_left
        clipped_height = clipped_bottom - clipped_top
        
        if clipped_width <= 0 or clipped_height <= 0:
            return None
        
        return {
            'left': clipped_left,
            'top': clipped_top,
            'width': clipped_width,
            'height': clipped_height
        }

    def capture_window(self, window):
        """Capture une fenêtre spécifique"""
        try:
            print(f"Capture de la fenêtre: {window.title}")
            # Obtenir le handle de la fenêtre
            hwnd = window.hwnd
            
            # Vérifier que la fenêtre est toujours visible
            if not win32gui.IsWindowVisible(hwnd):
                raise Exception("La fenêtre n'est plus visible")
            
            # Obtenir la position de la fenêtre sur l'écran
            window_rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = window_rect
            
            # Calculer les dimensions de la fenêtre
            window_width = window_right - window_left
            window_height = window_bottom - window_top
            
            # Créer la zone de capture initiale
            capture_area = {
                'left': window_left,
                'top': window_top,
                'width': window_width,
                'height': window_height
            }
            
            # Clipper la zone aux limites des écrans et exclure la barre des tâches
            clipped_area = self.clip_to_screen_bounds(capture_area)
            
            if clipped_area:
                # Capturer la zone
                with mss.mss() as sct:
                    screenshot = sct.grab(clipped_area)
                    
                    # Sauvegarder l'image
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"MultiScreenCapt-Clikdoo_window_{window.title.replace(' ', '_').replace(':', '_')}_{timestamp}.png"
                    filepath = os.path.join(self.settings.get_save_directory(), filename)
                    
                    # Convertir en PIL Image et sauvegarder
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    img.save(filepath)
                    
                    print(f"Capture de fenêtre sauvegardée: {filepath}")
                    # Feedback visuel de succès
                    self.show_window_capture_feedback(window)
                    return filepath
            else:
                print("Zone de capture invalide")
                self.show_window_capture_error(window)
                return None
                
        except Exception as e:
            print(f"Erreur lors de la capture de la fenêtre {window.title}: {e}")
            # Feedback visuel d'erreur
            self.show_window_capture_error(window)
            return None
    
    def show_window_capture_feedback(self, window):
        """Affiche un feedback visuel temporaire pour confirmer la capture de fenêtre"""
        # Trouver le bouton de capture pour cette fenêtre
        for widget in self.window_canvas_frame.winfo_children():
            if hasattr(widget, 'window_info') and widget.window_info == window:
                # Chercher le bouton de capture dans ce widget
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):  # Le frame d'info
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button):
                                # Sauvegarder le texte original
                                original_text = grandchild.cget('text')
                                
                                # Changer temporairement le texte
                                grandchild.configure(text="✓ " + get_text(self.current_language, 'window_capture_success'))
                                
                                # Restaurer le texte original après 1.5 secondes
                                self.root.after(1500, lambda btn=grandchild, text=original_text: btn.configure(text=text))
                                return
    
    def show_window_capture_error(self, window):
        """Affiche un feedback visuel temporaire pour indiquer une erreur de capture de fenêtre"""
        # Trouver le bouton de capture pour cette fenêtre
        for widget in self.window_canvas_frame.winfo_children():
            if hasattr(widget, 'window_info') and widget.window_info == window:
                # Chercher le bouton de capture dans ce widget
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):  # Le frame d'info
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button):
                                # Sauvegarder le texte original
                                original_text = grandchild.cget('text')
                                
                                # Changer temporairement le texte
                                grandchild.configure(text="✗ " + get_text(self.current_language, 'window_capture_error'))
                                
                                # Restaurer le texte original après 2 secondes
                                self.root.after(2000, lambda btn=grandchild, text=original_text: btn.configure(text=text))
                                return
    
    def show_capture_feedback(self, screen):
        """Affiche un feedback visuel temporaire pour confirmer la capture"""
        # Trouver le bouton de capture pour cet écran
        for widget in self.canvas_frame.winfo_children():
            if hasattr(widget, 'screen_info') and widget.screen_info == screen:
                # Chercher le bouton de capture dans ce widget
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):  # Le frame d'info
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button):
                                # Sauvegarder le texte original
                                original_text = grandchild.cget('text')
                                
                                # Changer temporairement le texte
                                grandchild.configure(text="✓ " + get_text(self.current_language, 'capture_saved'))
                                
                                # Restaurer le texte original après 1.5 secondes
                                self.root.after(1500, lambda btn=grandchild, text=original_text: btn.configure(text=text))
                                return
    
    def show_capture_error(self, screen):
        """Affiche un feedback visuel temporaire pour indiquer une erreur"""
        # Trouver le bouton de capture pour cet écran
        for widget in self.canvas_frame.winfo_children():
            if hasattr(widget, 'screen_info') and widget.screen_info == screen:
                # Chercher le bouton de capture dans ce widget
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):  # Le frame d'info
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button):
                                # Sauvegarder le texte original
                                original_text = grandchild.cget('text')
                                
                                # Changer temporairement le texte
                                grandchild.configure(text="✗ " + get_text(self.current_language, 'capture_error'))
                                
                                # Restaurer le texte original après 2 secondes
                                self.root.after(2000, lambda btn=grandchild, text=original_text: btn.configure(text=text))
                                return

def main():
    # Set DPI awareness for the application
    try:
        import ctypes
        # Set process DPI awareness to per-monitor
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception as e:
        print(f"Could not set DPI awareness: {e}")
        try:
            # Fallback to system DPI awareness
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e2:
            print(f"Could not set system DPI awareness: {e2}")
    
    root = tk.Tk()
    app = SmartCapture(root)
    root.mainloop()

if __name__ == "__main__":
    main() 