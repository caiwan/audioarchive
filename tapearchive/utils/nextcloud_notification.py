import requests
from requests.auth import HTTPBasicAuth


def nextcloud_notification_send_message(host, notify_user, short_message, long_message, user, passwd, https=True):
    protocol = "https" if https else "http"
    payload = {"shortMessage": short_message, "longMessage": long_message}
    url = f"{protocol}://{host}/ocs/v2.php/apps/notifications/api/v1/admin_notifications/{notify_user}"
    headers = {"OCS-APIREQUEST": "true"}

    return requests.post(url, data=payload, headers=headers, auth=HTTPBasicAuth(user, passwd))
