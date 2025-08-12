# MultiScreenCapt-Clikdoo-v1.0

Une application simple et efficace pour capturer des écrans multiples et des fenêtres d'applications sur Windows.

## Fonctionnalités

- **Détection automatique** : Détecte automatiquement tous les écrans connectés
- **Capture d'écrans** : Capture complète d'écrans multiples avec support DPI
- **Capture de fenêtres** : Capture de fenêtres d'applications ouvertes
- **Interface en onglets** : Interface moderne avec onglets Écrans et Fenêtres
- **Interface visuelle** : Affiche un aperçu de chaque écran avec ses dimensions
- **Capture simple** : Cliquez sur un écran/fenêtre ou son bouton pour le capturer
- **Sauvegarde personnalisée** : Choisissez où sauvegarder vos captures
- **Format PNG** : Toutes les captures sont sauvegardées en haute qualité PNG
- **Support multi-langues** : Interface en français et anglais

## Installation

1. **Installer Python** (version 3.7 ou plus récente)
   - Téléchargez depuis [python.org](https://www.python.org/downloads/)

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **(Optionnel) Construire l'exécutable**
   ```bash
   pyinstaller MultiScreenCapt-Clikdoo-v1.0.spec
   ```

## Utilisation

1. **Lancer l'application**
   ```bash
   python main.py
   ```

2. **Choisir le dossier de sauvegarde** (optionnel)
   - Par défaut (par utilisateur) : `~/Pictures/MultiScreenCapt-Clikdoo`
   - Cliquez sur "Parcourir" pour changer

3. **Capturer un écran**
   - Allez dans l'onglet "Écrans"
   - Cliquez sur l'aperçu de l'écran ou le bouton "Capturer cet écran"
   - La capture sera automatiquement sauvegardée avec un timestamp

4. **Capturer une fenêtre**
   - Allez dans l'onglet "Fenêtres"
   - Cliquez sur l'aperçu de la fenêtre ou le bouton "Capturer cette fenêtre"
   - La capture sera automatiquement sauvegardée avec un timestamp

## Structure des fichiers

```
MultiScreenCapt-Clikdoo-v1.0/
├── main.py              # Application principale
├── settings.py          # Gestion des paramètres
├── translations.py      # Système de traductions
├── requirements.txt     # Dépendances Python
└── README.md           # Ce fichier
```

## Dépendances

- **Pillow** : Manipulation d'images
- **pyautogui** : Capture d'écran
- **screeninfo** : Détection des écrans
- **mss** : Capture d'écran avancée
- **pywinauto** : Détection de fenêtres
- **pywin32** : API Windows
- **tkinter** : Interface graphique (inclus avec Python)

## Notes

- L'application fonctionne uniquement sur Windows
- Les captures sont nommées avec le format : `MultiScreenCapt-Clikdoo_YYYY-MM-DD_HH-MM-SS.png`
- L'interface s'adapte automatiquement au nombre d'écrans détectés
- Support complet des écrans avec mise à l'échelle DPI (150%, etc.) 