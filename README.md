# onboard-grades-tracker

## Description

Ce projet est un script Python conçu pour interagir avec la plateforme **Onboard** de l'École Centrale de Nantes. Il permet de télécharger, comparer et sauvegarder les notes académiques au format CSV, puis d'envoyer un mail de notification lorsqu'une nouvelle note apparaît dans la liste. Le script prend en charge les langues française et anglaise pour les données.

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
git clone https://github.com/votre-utilisateur/onboard-grades-tracker.git
```

2. Créez un fichier `.env` à la racine du projet et ajoutez-y les variables suivantes en remplaçant par les informations adéquates. Les chaînes de caractères sont saisies sans guillemets.
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

# Informations sur l'email pour l'envoie de la notification
SENDER_EMAIL=example@domaine.com
SMTP_PASSWORD=your_smtp_password

# Informations sur l'email pour la réception de la notification
RECEIVER_EMAIL=recipient@domaine.com
```

Pour certaines messageries, il faudra créer un mot de passe d'application ([instructions](https://support.google.com/accounts/answer/185833?hl=fr) pour gmail). Cela permet entre autres de ne pas stocker en clair votre mot de passe sur la machine.

3. Exécutez le script souhaité. Par exemple :
```bash
python3 ~/onboard-grades-tracker/main.py
```

Les notes seront téléchargées et sauvegardées dans le fichier `grades.csv`.
Si une nouvelle note apparaît, un mail sera envoyé à l'adresse spécifiée.

### Automatisation

Pour automatiser l'exécution du script, vous pouvez utiliser **cron** (sous Linux/macOS) ou le Planificateur de tâches (sous Windows). Voici un exemple d'automatisation avec **cron** :

1. Créez un fichier `launch.sh` à la racine du projet avec le contenu suivant :
  ```bash
  #!/bin/bash
  # If the script is located in your home directory, use the following:
  SCRIPT_DIR="$HOME/onboard-grades-tracker"
  LOG_FILE="$SCRIPT_DIR/cron.log"
  echo "$(date) - Start script" >> $LOG_FILE
  /usr/bin/python3 $SCRIPT_DIR/main.py >> $LOG_FILE 2>&1
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
  */5 * * * * /bin/bash $HOME/onboard-grades-tracker/launch.sh
  ```

4. Sauvegardez et quittez l'éditeur. Votre script sera désormais exécuté automatiquement à l'heure spécifiée.

Pour les utilisateurs de Windows, vous pouvez configurer une tâche planifiée pour exécuter le script `launch.sh` ou directement le fichier Python.

**Note :** Assurez-vous que les chemins et permissions sont correctement configurés pour éviter les erreurs lors de l'exécution automatique. En particulier sur macOS, les dossiers Bureau, Documents et Téléchargement on par défaut des accès restreint : il est préférable de placer le script dans un autre dossier.

## Auteurs

- [Philippe Pernet](https://github.com/PhPernet)
- [Jérémy Rozier](https://github.com/JeremyRozier)
