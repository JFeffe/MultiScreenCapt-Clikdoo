#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'exécutable compilé
"""

import subprocess
import os
import time

def test_executable():
    """Teste l'exécutable compilé"""
    exe_path = os.path.join("dist", "MultiScreenCapt-Clikdoo-v1.0.exe")
    
    if not os.path.exists(exe_path):
        print("❌ L'exécutable n'existe pas!")
        return False
    
    print(f"✅ Exécutable trouvé: {exe_path}")
    print(f"📁 Taille: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
    
    print("\n🚀 Lancement de l'exécutable...")
    print("⚠️  L'application va se lancer. Testez le bouton 'Gérer les chemins'.")
    print("⚠️  Fermez l'application quand vous avez fini de tester.")
    
    try:
        # Lancer l'exécutable
        process = subprocess.Popen([exe_path], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print("✅ L'exécutable a été lancé avec succès!")
        print("⏳ En attente de la fermeture de l'application...")
        
        # Attendre que le processus se termine
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print("✅ L'application s'est fermée normalement")
        else:
            print(f"⚠️  L'application s'est fermée avec le code: {process.returncode}")
        
        if stdout:
            print(f"📤 Sortie standard:\n{stdout}")
        
        if stderr:
            print(f"📤 Sortie d'erreur:\n{stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        return False

def main():
    """Fonction principale"""
    print("=== TEST DE L'EXÉCUTABLE ===")
    
    success = test_executable()
    
    if success:
        print("\n🎉 Test terminé avec succès!")
    else:
        print("\n❌ Test échoué!")
    
    print("=== FIN DU TEST ===")

if __name__ == "__main__":
    main() 