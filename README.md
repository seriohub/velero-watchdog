# Velero-Watchdog

> [!WARNING]  
**Attention Users:** This project is in active development, and certain tools or features might still be under construction. We kindly urge you to exercise caution while utilizing the tools within this environment. While every effort is being made to ensure the stability and reliability of the project, there could be unexpected behaviors or limited functionalities in some areas.
We highly recommend thoroughly testing the project in non-production or sandbox environments before implementing it in critical or production systems. Your feedback is invaluable to us; if you encounter any issues or have suggestions for improvement, please feel free to [report them](https://github.com/seriohub/velero-watchdog/issues). Your input helps us enhance the project's performance and user experience.
Thank you for your understanding and cooperation.

> [!IMPORTANT]
> Velero-Watchdog project is part of a project consisting of three modules:
> - [Velero-API](https://github.com/seriohub/velero-api/)
> - [Velero-UI](https://github.com/seriohub/velero-ui/)
> - Velero-Watchdog

> [!TIP]
> [Helm installation is recommended](https://github.com/seriohub/velero-helm/)

## Description

This Python project is designed to monitor the status of Velero in Kubernetes environments and alert when something is not working.
It provides efficient ways to check the backups status.
This project can be used in standalone mode or better with [velero-ui](https://github.com/seriohub/velero-ui) project.

## Features

### 1. Backup Status Monitoring

The project monitors the backup status of Kubernetes clusters.

### 2. Schedule Change Monitoring

Monitor and alert if the schedule changes.

### 3. Channels notifications

Receive the alerts and the solved messages via notifications channels, allowing immediate action.

Available plugin:
- Email
- Slack
- Telegram

## Requirements

- Python 3.x
- kubectl cli (if [Run in kubernetes](#run-in-kubernetes))
- Telegram API credentials (if telegram notification is enabled)
- SMTP and user account (if email notification is enabled)

## Configuration

| FIELD                          | TYPE   | DEFAULT | DESCRIPTION                                                                                                                                              |
|--------------------------------|--------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DEBUG`                        | Bool   | False   | View debugging information.                                                                                                                              |
| `LOG_SAVE`                     | Bool   | False   | Save log to files                                                                                                                                        |
| `PROCESS_LOAD_KUBE_CONFIG`*    | Bool   | True    | Set False if it runs on k8s.                                                                                                                             |
| `PROCESS_KUBE_CONFIG`          | String |         | Path to the kube config file. This is mandatory when the script runs outside the Kubernetes cluster, either in a docker container or as a native script. |
| `PROCESS_CLUSTER_NAME` * **    | String |         | Force the cluster name and it appears in the message                                                                                                     |
| `PROCESS_CYCLE_SEC`            | Int    | 120     | Cycle time (seconds)                                                                                                                                     |
| `TELEGRAM_ENABLE`    *         | Bool   | True    | Enable telegram notification                                                                                                                             |
| `TELEGRAM_API_TOKEN` *         | String |         | Token for access to Telegram bot via Http API                                                                                                            |
| `TELEGRAM_CHAT_ID`   *         | String |         | Telegram chat id where send the notifications                                                                                                            |
| `EMAIL_ENABLE`       *         | Bool   | False   | Enable email notification                                                                                                                                |
| `EMAIL_SMTP_SERVER`  *         | String |         | SMTP server                                                                                                                                              |
| `EMAIL_SMTP_PORT`    *         | int    | 587     | SMTP port                                                                                                                                                |
| `EMAIL_ACCOUNT`      *         | String |         | user name account                                                                                                                                        |
| `EMAIL_PASSWORD`     *         | String |         | password account                                                                                                                                         |
| `EMAIL_RECIPIENTS`   *         | Bool   |         | Email recipients                                                                                                                                         |
| `SLACK_ENABLE`       *         | Bool   |         | Enable Slack notification                                                                                                                                |
| `SLACK_CHANNEL`      *         | Bool   |         | Channel id where sens the notification                                                                                                                   |
| `SLACK_TOKEN`        *         | Bool   |         | Token for access to Slack via Http API                                                                                                                   |
| `BACKUP_ENABLE`                | Bool   | True    | Enable watcher for backups without schedule or last backup for each schedule                                                                             |
| `EXPIRES_DAYS_WARNING`         | int    | 10      | Number of days to backup expiration below which to display a warning about the backup                                                                    |
| `SCHEDULE_ENABLE`              | Bool   | True    | Enable watcher for schedule                                                                                                                              |
| `K8S_INCLUSTER_MODE` **        | Bool   | False   | Enable in cluster mode                                                                                                                                   |
| `IGNORE_NM_1`                  | String |         | regex to ignore a namespace or a group of namespaces                                                                                                     |
| `IGNORE_NM_2`                  | String |         | regex to ignore a namespace or a group of namespaces                                                                                                     |
| `IGNORE_NM_3`                  | String |         | regex to ignore a namespace or a group of namespaces                                                                                                     |
| `NOTIFICATION_SKIP_COMPLETED`  | Bool   | True    | Skip notification new completed backup                                                                                                                   |
| `NOTIFICATION_SKIP_INPROGRESS` | Bool   | True    | Skip notification new in progress backup                                                                                                                 |
| `NOTIFICATION_SKIP_REMOVED`    | Bool   | True    | Skip notification backup removed                                                                                                                         |


- \* Mandatory parameters
- \** Mandatory if it is deployed on cluster

## Installation

Clone the repository:

  ``` bash
    git clone https://github.com/seriohub/velero-watchdog.git
    cd velero-watchdog
  ```

### Run native

1. Navigate to the [src](src) folder

2. Dependencies installation:

    ``` bash
    pip install -r requirements.txt
    ```

3. Configuration

    Create and edit .env file under src folder, you can start from [.env.template](src/.env.template) under [src](src) folder
    Setup mandatory parameters in the src/.env file if runs it in the native mode

4. Usage

    Run the main script:

    ``` bash
    python3 main.py
    ```
   
   Run as daemon:

    ``` bash
    python3 main.py --daemon
    ```

### Run in Kubernetes

#### Install with HELM

   See [helm readme](https://github.com/seriohub/velero-helm)

#### Install with Kubernetes YAML

1. Setup docker image:

   >   [!INFO]  
   You can use skip the *Setup docker image* and use a deployed image published on DockerHub.</br>
   Docker hub: <https://hub.docker.com/r/dserio83/velero-watchdog>

   1. Navigate to the root folder
   2. Build image

        ``` bash
        docker build --target velero-watchdog -t <your-register>/<your-user>/velero-watchdog:<tag> -f ./docker/Dockerfile .
        ```

   3. Push image

        ``` bash
        docker push <your-register>/<your-user>/velero-watchdog --all-tags
        ```

      >[!INFO]  
      Alternative you can use skip the *Build image* and *Push image* steps and use a deployed image published on DockerHub.<br>
      Edit the .env file:
      **K8SW_DOCKER_REGISTRY=dserio83** <br>
      More info: https://hub.docker.com/r/dserio83/velero-watchdog

2. Kubernetes create objects

   1. Navigate to the [k8s](k8s) folder

   2. Create namespace (If it does not exist, the namespace should already be created if you have installed the Velero API):

        ``` bash
        kubectl create ns velero-ui
        ```

   3. Create the ConfigMap:
   
      >   [!WARNING]  
      Set the parameters in the [200_config_map.yaml](k8s/200_config_map.yaml) file before applying it according to your environment.

      ``` bash
      kubectl apply -f 200_config_map.yaml -n velero-ui
      ```

   4. Create the RBAC:

       ``` bash
       kubectl apply -f 210_rbac.yaml -n velero-ui
       ```
  
   5. Create the Cluster Ip Service:

       ``` bash
       kubectl apply -f 230_cluster_ip.yaml -n velero-ui
       ```
  
   6. Create the Deployment:

      ``` bash
      kubectl apply -f 240_cronjob.yaml -n velero-ui
      ```

## Test Environment

The project is developed, tested and put into production on several clusters with the following configuration

1. Kubernetes v1.28.2
2. Velero Server 1.11.1/Client v1.11.1
3. Velero Server 1.12.1/Client v1.12.1

## How to Contribute

1. Fork the project
2. Create your feature branch

    ``` bash
    git checkout -b feature/new-feature
    ```

3. Commit your changes

    ``` bash
   git commit -m 'Add new feature'
   ```

4. Push to the branch

    ``` bash
   git push origin feature/new-feature
   ```

5. Create a new pull request

## License

This project is licensed under the [Apache 2.0 license](LICENSE).

---

Feel free to modify this template according to your project's specific requirements.

In case you need more functionality, create a PR. If you find a bug, open a ticket.
