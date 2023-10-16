# Velero-Watchdog

> [!WARNING]  
**Attention Users:** This project is in active development, and certain tools or features might still be under construction. We kindly urge you to exercise caution while utilizing the tools within this environment. While every effort is being made to ensure the stability and reliability of the project, there could be unexpected behaviors or limited functionalities in some areas.
We highly recommend thoroughly testing the project in non-production or sandbox environments before implementing it in critical or production systems. Your feedback is invaluable to us; if you encounter any issues or have suggestions for improvement, please feel free to [report them](https://github.com/seriohub/velero-watchdog/issues). Your input helps us enhance the project's performance and user experience.
Thank you for your understanding and cooperation.

## Description

This Python project is designed to monitor the status of Velero backups in Kubernetes environments. 
It provides efficient ways to check the backup status, retrieve detailed or summarized reports, and receive notifications via Telegram.

## Features

### 1. Backup Status Monitoring

The project monitors the backup status of Kubernetes clusters.

### 2. Quick Status Check

Easily view the status of the last backup for each schedule to assess the health of your backups promptly.

### 3. Comprehensive and Concise Reports

Generate detailed reports to get in-depth insights into backup statuses. Alternatively, obtain concise reports focusing solely on critical issues for a quick overview.

### 4. Telegram Integration

Receive backup status notifications and reports ([details](example/report-telegram.md), [summary](example/summary-report-telegram.md)) directly via Telegram, allowing for immediate awareness and action.

## Requirements

- Python 3.x
- Velero
- Telegram API credentials

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/seriohub/velero-watchdog.git
   cd project-directory
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure KUBE_CONFIG_FILE in configuration file (`.env`).

4. Set up Telegram integration by providing API credentials in the configuration file.

## Configuration

Create the `.env` file under **src** folder to customize settings such as show debug info, validation_day, notification and Telegram integration.

```
DEBUG_ON=<FALSE|TRUE>
EXPIRES_DAYS_WARNING=<INT>
TELEGRAM_API_TOKEN=<TELEGRAM_API_TOKEN>
TELEGRAM_CHAT_ID=<TELEGRAM_CHAT_ID>
KUBE_CONFIG_FILE=<PATH_TO_CONFIG_FILE>
```


| FIELD                  | TYPE   | DECRIPTION                                                                             |
|------------------------|--------|----------------------------------------------------------------------------------------|
| `DEBUG_ON`             | Bool   | View debugging information.                                                            |
| `EXPIRES_DAYS_WARNING` | Int    | Number of days to backup expiration below which to display a warning about the backup. |
| `TELEGRAM_API_TOKEN`   | String | Token needed to use your telegram bot via Http API                                     |
| `TELEGRAM_CHAT_ID`     | String | Telegram chat id on which to send notifications.                                       |
| `KUBE_CONFIG_FILE`     | String | Path to your kubeconfig file to access cluster.                                        |


## Usage

1. Run the main script:
   ```
   python3 main.py
   ```

   Choose an option from the menu to monitor backup status, view reports, or send Telegram notifications.


2. Run the desired command directly:
   ```
   python3 main.py <command>
   python3 main.py get-backups-status
   ```

3. Schedule notifications, for example, you can use cron:
   ```commandline
       30 08 * * *	python3 <path-to-file>/main.py report-tgm-sum
   ```

## Test Environment

The project is developed, tested and put into production on several clusters with the following configuration

1. Kubernetes v1.28.2
2. Velero Server Version: v1.12.0
3. Restic integration as Kubernetes volumes backup

## How to Contribute

1. Fork the project
2. Create your feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a new pull request

## License

This project is licensed under the [MIT License](LICENSE).

---

Feel free to modify this template according to your project's specific requirements.