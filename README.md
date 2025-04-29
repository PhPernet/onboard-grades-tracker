# onboard-notes-tracker

## Description

Ce projet est un script Python conçu pour interagir avec la plateforme **Onboard** de l'École Centrale de Nantes. Il permet de télécharger, comparer et sauvegarder les notes académiques au format CSV. Le script prend en charge les langues française et anglaise pour les données.

## Fonctionnalités

- Connexion automatique à la plateforme Onboard.
- Téléchargement des notes académiques sous forme de fichier CSV.
- Comparaison des nouvelles notes avec les anciennes pour détecter les mises à jour.
- Sauvegarde des notes mises à jour dans un fichier CSV local.
- Envoie d'un mail pour notifier de l'ajout d'une note.

## Prérequis

- Python 3.7 ou version ultérieure.
- Les bibliothèques Python suivantes doivent être installées (elles ne sont pas incluses par défaut) :
  - `requests`
  - `beautifulsoup4`
  - `pandas`
  - `python-dotenv`

## Utilisation
1. Clonez ce dépôt sur votre machine locale :
```bash
git clone https://github.com/votre-utilisateur/onboard-notes-tracker.git
```

2. Créez un fichier `.env` à la racine du projet et ajoutez-y les variables suivantes avec des valeurs fictives :
```env
# Identifiants de connexion
LOGIN=your_onboard_login
PASSWORD=your_password

# Configuration SMTP
SMTP_SERVER=smtp.example.com
# Pour Gmail, utilisez 465 ou 587
# Pour Outlook, utilisez 587
# Pour Yahoo, utilisez 465
SMTP_PORT=465

# Informations sur l'email
SENDER_EMAIL=example@domaine.com
SMTP_PASSWORD=your_smtp_password
RECEIVER_EMAIL=recipient@domaine.com
```

3. Exécutez le script souhaité.

Les notes seront téléchargées et sauvegardées dans le fichier `notes.csv`.
Si une nouvelle note apparaît, un mail sera envoyé à l'adresse spécifiée.

### Automatisation

Pour automatiser l'exécution du script, vous pouvez utiliser **cron** (sous Linux/macOS) ou le Planificateur de tâches (sous Windows). Voici un exemple d'automatisation avec **cron** :

1. Créez un fichier `launch.sh` à la racine du projet avec le contenu suivant :
  ```bash
  #!/bin/bash
  # If the script located in your Home directory.
  LOG_FILE="$HOME/onboard-notes-tracker/cron.log"
  echo "$(date) - Start script" >> $LOG_FILE
  /usr/bin/python3 $HOME/onboard-notes-tracker/main.py >> $LOG_FILE 2>&1
  echo "$(date) - End script" >> $LOG_FILE
  echo "" >> $LOG_FILE
  ```

2. Rendez le script exécutable :
  ```bash
  chmod +x launch.sh
  ```

3. Ajoutez une tâche cron pour exécuter le script à intervalles réguliers. Par exemple, pour l'exécuter tous les jours à 8h :
  ```bash
  crontab -e
  ```

  Ajoutez la ligne suivante pour exécuter le script toutes les 5 minutes :
  ```bash
  */5 * * * * /bin/bash $HOME/onboard-notes-tracker/launch.sh
  ```

4. Sauvegardez et quittez l'éditeur. Votre script sera désormais exécuté automatiquement à l'heure spécifiée.

Pour les utilisateurs de Windows, vous pouvez configurer une tâche planifiée pour exécuter le script `launch.sh` ou directement le fichier Python.

**Note :** Assurez-vous que les chemins et permissions sont correctement configurés pour éviter les erreurs lors de l'exécution automatique. En particulier sur macOS, les dossiers Bureau, Documents et Téléchargement on par défaut des accès restreint : il est préférable de placer le script dans un autre dossier.
