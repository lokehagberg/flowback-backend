# Flowback Notification Module
This  only contains some heads-up information about how to set up Notifications for any given Model

## Creating a Channel
To create a Channel, inherit NotifiableModel to the class:

```python
from flowback.common.models import BaseModel
from flowback.notification.models import NotifiableModel, NotificationChannel
from flowback.group.models import Group
from django.db import models


class ExampleModel(BaseModel, NotifiableModel):
    example_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    
    @property
    def notification_data(self):
        # Data contains default data included in every notification
        return dict(example_id=self.id,
                    group_id=self.example_group.id)

    # Notification tag functions should start with 'notify_', must call on notification_channel.notify()
    def notify_group(self, action: NotificationChannel.Action, message: str, subscription_filters: dict, test_data: str):
        
        # Get all relevant fields except for "self"
        params = locals()
        params.pop('self')
        
        # Forward the data to notification_channel
        return self.notification_channel.notify(**params)
```
* Note that deleting the `ExampleModel` instance will also delete the NotificationChannel.
* The `subsription_filters`, as well as `subscription_q_filters` fields for `self.notification_channel.notify` allows 
you to pass filters to limit which users that will receive the notification
* The `tag` field in `self.notification_channel.notify` if left empty, will get the tag from the calling function, 
if it matches the pattern `notify_<tag_name>`. Otherwise it'll raise an error.
* The kwarg parameters for `notify` will be used later for documentation. If you wish to pass a kwarg without it being
documented, add an underscore at the beginning of the field name.