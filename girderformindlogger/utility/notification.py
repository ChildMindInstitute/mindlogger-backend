from pyfcm.baseapi import BaseAPI


class FirebaseNotification(BaseAPI):
    def notify_multiple_individual_devices(self,
                                           profiles=None,
                                           message_title=None,
                                           message_body=None,
                                           data_message=None
                                           ):
        payloads = []
        for profile in profiles:
            if len(profile['deviceId']):
                profile['badge'] = profile.get('badge', 0) + 1
                payloads.append(self.parse_payload(
                    registration_ids=[profile['deviceId']],
                    message_body=message_body,
                    message_title=message_title,
                    data_message=data_message,
                    badge=profile.get('badge', 0),
                ))
        self.send_request(payloads, timeout=5)
        return self.parse_responses()
