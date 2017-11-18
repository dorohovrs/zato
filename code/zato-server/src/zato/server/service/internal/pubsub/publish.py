# -*- coding: utf-8 -*-

"""
Copyright (C) 2017, Zato Source s.r.o. https://zato.io

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
from contextlib import closing

# datetutil
from dateparser import parse as dt_parse

# gevent
from gevent import spawn

# Zato
from zato.common import DATA_FORMAT
from zato.common.exception import Forbidden, NotFound, ServiceUnavailable
from zato.common.odb.query_pubsub import get_topic_depth, incr_topic_depth, insert_queue_messages, insert_topic_messages, \
     update_publish_metadata
from zato.common.pubsub import new_msg_id
from zato.common.time_util import datetime_to_ms, utcnow_as_ms
from zato.common.util import spawn_greenlet
from zato.server.pubsub import get_expiration, get_priority
from zato.server.service import AsIs, Int, List
from zato.server.service.internal import AdminService

# ################################################################################################################################

_JSON = DATA_FORMAT.JSON

# ################################################################################################################################

class Publish(AdminService):
    """ Actual implementation of message publishing exposed through other services to the outside world.
    """
    class SimpleIO:
        input_required = ('topic_name',)
        input_optional = ('data', List('data_list'), AsIs('msg_id'), 'has_gd', Int('priority'), Int('expiration'), 'mime_type',
            AsIs('correl_id'), 'in_reply_to', AsIs('ext_client_id'), 'ext_pub_time', 'pattern_matched', 'security_id',
            'ws_channel_id', 'service_id', 'data_parsed', 'meta', AsIs('group_id'),
            Int('position_in_group'), 'endpoint_id')
        output_optional = (AsIs('msg_id'), List('msg_id_list'))

# ################################################################################################################################

    def _get_message(self, topic, input, now, pattern_matched, endpoint_id):

        priority = get_priority(self.cid, input)
        expiration = get_expiration(self.cid, input)
        expiration_time = now + (expiration * 1000)

        pub_msg_id = input.get('msg_id', '').encode('utf8') or new_msg_id()
        has_gd = input['has_gd'] if isinstance(input.get('has_gd'), bool) else topic.has_gd

        pub_correl_id = input.get('correl_id')
        in_reply_to = input.get('in_reply_to')
        ext_client_id = input.get('ext_client_id')

        ext_pub_time = input.get('ext_pub_time')
        if ext_pub_time:
            ext_pub_time = dt_parse(ext_pub_time)
            ext_pub_time = datetime_to_ms(ext_pub_time)

        pub_correl_id = pub_correl_id.encode('utf8') if pub_correl_id else None
        in_reply_to = in_reply_to.encode('utf8') if in_reply_to else None
        ext_client_id = ext_client_id.encode('utf8') if ext_client_id else None

        ps_msg = {
            'pub_msg_id': pub_msg_id,
            'pub_correl_id': pub_correl_id,
            'in_reply_to': in_reply_to,
            'pub_time': now,
            'pattern_matched': pattern_matched,
            'data': input['data'].encode('utf8'),
            'data_prefix': input['data'][:2048].encode('utf8'),
            'data_prefix_short': input['data'][:64].encode('utf8'),
            'mime_type': input.get('mime_type', 'text/plain'),
            'size': len(input['data']),
            'priority': priority,
            'expiration': expiration,
            'expiration_time': expiration_time,
            'published_by_id': endpoint_id,
            'topic_id': topic.id,
            'cluster_id': self.server.cluster_id,
            'has_gd': has_gd,
            'ext_client_id': ext_client_id,
            'ext_pub_time': ext_pub_time,
            'group_id': input.get('group_id') or None,
            'position_in_group': input.get('position_in_group') or None,
        }

        return ps_msg

# ################################################################################################################################

    def _get_messages_from_data(self, topic, data_list, input, now, pattern_matched, endpoint_id):

        ps_msg_list = []

        if data_list and isinstance(data_list, (list, tuple)):
            for elem in data_list:
                ps_msg_list.append(self._get_message(topic, elem, now, pattern_matched, endpoint_id))
        else:
            ps_msg_list.append(self._get_message(topic, input, now, pattern_matched, endpoint_id))

        return ps_msg_list

# ################################################################################################################################

    def _notify_pubsub_task_runners(self, topic_name, subscriptions):
        spawn_greenlet(self.invoke, 'zato.pubsub.after-publish', {
            'topic_name':topic_name,
            'subscriptions': subscriptions
        })

# ################################################################################################################################

    def get_pattern_matched(self, endpoint_id, input):
        """ Returns a publication pattern matched that allows the endpoint to publish messages
        or raises an exception if no pattern was matched. Takes into account various IDs possibly given on input,
        depending on what our caller wanted to provide.
        """
        pubsub = self.server.worker_store.pubsub
        security_id = input.security_id or None
        ws_channel_id = input.ws_channel_id or None

        if not endpoint_id:

            if security_id:
                endpoint_id = pubsub.get_endpoint_id_by_sec_id(security_id)
            elif ws_channel_id:
                endpoint_id = pubsub.get_endpoint_id_by_ws_channel_id(ws_channel_id)
            else:
                raise NotImplementedError('To be implemented')

            kwargs = {'security_id':security_id} if security_id else {'ws_channel_id':ws_channel_id}
            pattern_matched = pubsub.is_allowed_pub_topic(input.topic_name, **kwargs)

        else:
            pattern_matched = pubsub.is_allowed_pub_topic_by_endpoint_id(input.topic_name, endpoint_id)

        # Not allowed, raise an exception in that case
        if not pattern_matched:
            raise Forbidden(self.cid)

        # Alright, we are in
        return pattern_matched

# ################################################################################################################################

    def handle(self):

        input = self.request.input
        pubsub = self.server.worker_store.pubsub
        endpoint_id = input.endpoint_id

        # Will return publication pattern matched or raise an exception that we don't catch
        pattern_matched = self.get_pattern_matched(self, input)

        try:
            topic = pubsub.get_topic_by_name(input.topic_name)
        except KeyError:
            raise NotFound(self.cid, 'No such topic `{}`'.format(input.topic_name))

        # We always count time in milliseconds since UNIX epoch
        now = utcnow_as_ms()

        # If input.data is a list, it means that it is a list of messages, each of which has its own
        # metadata. Otherwise, it's a string to publish and other input parameters describe it.
        data_list = input.data_list if input.data_list else None
        ps_msg_list = self._get_messages_from_data(topic, data_list, input, now, pattern_matched, endpoint_id)

        # Get all subscribers for that topic from local worker store
        subscriptions_by_topic = pubsub.get_subscriptions_by_topic(input.topic_name)

        cluster_id = self.server.cluster_id

        # Operate under a global lock for that topic to rule out any interference
        with self.lock('zato.pubsub.publish.%s' % input.topic_name):

            with closing(self.odb.session()) as session:

                # Get current depth of this topic
                current_depth = get_topic_depth(session, cluster_id, topic.id)

                # Abort if max depth is already reached ..
                if current_depth >= topic.max_depth:
                    raise ServiceUnavailable(self.cid, 'Max depth already reached for `{}`'.format(topic.name))

                # .. otherwise, update current depth and timestamp of last publication to the topic.
                else:
                    incr_topic_depth(session, cluster_id, now, len(ps_msg_list))

                # Publish messages - INSERT rows, each representing an individual message
                insert_topic_messages(session, self.cid, ps_msg_list)

                # Move messages to each subscriber's queue
                if subscriptions_by_topic:
                    insert_queue_messages(session, cluster_id, subscriptions_by_topic, ps_msg_list, topic.id)

                # Run an SQL commit for all queries above
                session.commit()

        # Update metadata in background
        spawn(self._update_pub_metadata, cluster_id, topic.id, endpoint_id, now, ps_msg_list, pattern_matched)

        # Also in background, notify pub/sub task runners that there are new messages for them
        if subscriptions_by_topic:
            self._notify_pubsub_task_runners(topic.name, subscriptions_by_topic)

        # Return either a single msg_id if there was only one message published or a list of message IDs,
        # one for each message published.
        if len(ps_msg_list) == 1:
            self.response.payload.msg_id = ps_msg_list[0]['pub_msg_id']
        else:
            self.response.payload.msg_id_list = [elem['pub_msg_id'] for elem in ps_msg_list]

# ################################################################################################################################

    def _update_pub_metadata(self, cluster_id, topic_id, endpoint_id, now, ps_msg_list, pattern_matched):
        """ Updates in background metadata about a topic and publisher after each publication.
        """
        last_pub_msg_id = ps_msg_list[-1]['pub_msg_id']
        last_pub_correl_id = ps_msg_list[-1]['pub_correl_id']
        last_ext_client_id = ps_msg_list[-1]['ext_client_id']
        last_in_reply_to = ps_msg_list[-1]['in_reply_to']

        with closing(self.odb.session()) as session:

            # Update last pub time and related metadata for topic and current publisher
            update_publish_metadata(session, cluster_id, topic_id, endpoint_id, now, ps_msg_list, pattern_matched,
                last_pub_msg_id, last_pub_correl_id, last_ext_client_id, last_in_reply_to)

            session.commit()

# ################################################################################################################################