# onboard-notes-tracker

## Description

Ce projet est un script Python conçu pour interagir avec la plateforme **Onboard** de l'École Centrale de Nantes. Il permet de télécharger, comparer et sauvegarder les notes académiques au format CSV. Le script prend en charge les langues française et anglaise pour les données.

## Fonctionnalités

- Connexion automatique à la plateforme Onboard.
- Téléchargement des notes académiques sous forme de fichier CSV.
- Comparaison des nouvelles notes avec les anciennes pour détecter les mises à jour.
- Sauvegarde des notes mises à jour dans un fichier CSV local.

## Structure du projet

- **`main-fr-only.py`** : Script pour télécharger et gérer les notes uniquement en français.
- **`main-fr-en.py`** : Script pour gérer les notes en français et en anglais.

## Prérequis

- Python 3.7 ou version ultérieure.
- Les bibliothèques Python suivantes :
  - `requests`
  - `beautifulsoup4`
  - `pandas`

## Utilisation
1. Clonez ce dépôt sur votre machine locale :
```bash
git clone https://github.com/votre-utilisateur/onboard-notes-tracker.git
```

2. Modifiez les identifiants de connexion dans le fichier Python que vous souhaitez utiliser (`LOGIN`, `PASSWORD` et `YEAR`).

3. Exécutez le script souhaité.

Les notes seront téléchargées et sauvegardées dans le fichier `notes.csv`.
