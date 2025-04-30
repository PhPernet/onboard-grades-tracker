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

Pour automatiser l'exécution du script, plusieurs options sont disponibles en fonction de votre système d'exploitation :

1. **Linux/macOS** : Utilisez **cron**, un outil intégré pour planifier des tâches récurrentes.
2. **Windows** : Utilisez le Planificateur de tâches pour configurer une exécution automatique.
3. **Docker** (optionnel) : Vous pouvez encapsuler le script dans un conteneur Docker et utiliser un orchestrateur pour gérer les exécutions.

#### Exemple avec cron (Linux/macOS)

Le fichier `launch.sh` inclus dans ce dépôt est conçu pour faciliter l'automatisation. Il gère les journaux et limite l'exécution à des plages horaires spécifiques.

1. Rendez le script exécutable :
   ```bash
   chmod +x launch.sh
   ```

2. Ajoutez une tâche cron pour exécuter le script à intervalles réguliers. Par exemple, pour l'exécuter toutes les 5 minutes :
   ```bash
   crontab -e
   ```

   Ajoutez la ligne suivante :
   ```bash
   */5 * * * * /bin/bash $HOME/onboard-grades-tracker/launch.sh
   ```

3. Sauvegardez et quittez l'éditeur. Votre script sera désormais exécuté automatiquement à l'heure spécifiée.

#### Exemple avec le Planificateur de tâches (Windows)

1. Ouvrez le Planificateur de tâches et créez une nouvelle tâche.

2. Configurez un déclencheur pour exécuter la tâche à intervalles réguliers (par exemple, toutes les 5 minutes).

3. Dans l'action, sélectionnez "Démarrer un programme" et indiquez le chemin vers `bash.exe` (fourni par Git Bash ou WSL).

4. Dans les arguments, ajoutez le chemin vers le fichier `launch.sh` :
   ```bash
   /path/to/launch.sh
   ```

5. Sauvegardez la tâche. Elle sera exécutée automatiquement selon la planification.

#### Notes importantes

- **Plages horaires** : Le fichier `launch.sh` inclut des variables pour limiter l'exécution à des plages horaires spécifiques (`START_HOUR` et `END_HOUR`).
- **Journaux** : Les logs sont enregistrés dans un fichier `cron.log` et sont automatiquement tronqués pour éviter une croissance excessive.
- **Permissions** : Assurez-vous que les chemins et permissions sont correctement configurés pour éviter les erreurs lors de l'exécution automatique. En particulier sur macOS, les dossiers Bureau, Documents et Téléchargement ont par défaut des accès restreints : il est préférable de placer le script dans un autre dossier.

## Auteurs

- [Philippe Pernet](https://github.com/PhPernet)
- [Jérémy Rozier](https://github.com/JeremyRozier)
