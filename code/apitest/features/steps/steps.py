# -*- coding: utf-8 -*-

"""
Copyright (C) 2014 Dariusz Suchojad <dsuch at zato.io>

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# Behave
from behave import given, then

# jsonpointer
from jsonpointer import resolve_pointer as get_pointer, set_pointer as _set_pointer

import base64
import json

# datadiff
from datadiff.tools import assert_equals

# Zato
from zato.apitest import steps as default_steps
from zato.apitest.steps.json import set_pointer
from zato.apitest.util import obtain_values, utcnow
from zato.apitest.steps.json import assert_value
from zato.apitest import INVALID

@given('I store a format string "{value}" under "{name}"')
def given_i_store_format_string_value_under_name(ctx, value, name):
    ctx.zato.user_ctx[name] = str(value).format(**ctx.zato.user_ctx)

@given('I store UTC now under "{name}" "{format}"')
@obtain_values
def given_i_store_utc_now_under_name(ctx, name, format):
    ctx.zato.user_ctx[name] = utcnow(format=ctx.zato.date_formats[format])


@then('JSON Pointer "{path}" is base64 JSON which pointer "{path2}" has "{value}"')
@obtain_values
def then_json_pointer_is_a_base64_object(ctx, path, path2, value):
    actual = get_pointer(ctx.zato.response.data_impl, path)
    decoded_value = json.loads(base64.b64decode(actual))
    actual = get_pointer(decoded_value, path2)

    return assert_equals(actual, value)

@then('JSON Pointer "{path}" isn\'t an empty list')
@obtain_values
def then_json_pointer_isnt_an_empty_list(ctx, path):
    actual = get_pointer(ctx.zato.response.data_impl, path)
    assert actual != [], 'Value `{}`, is an empty list'.format(actual)

@then('I store header "{header}" from response under "{name}"')
@util.obtain_values
def then_store_header_under_name(ctx, header, name):
    value = ctx.zato.response.data.headers.get(header, INVALID)
    ctx.zato.user_ctx[name] = value
    if value == INVALID:
        value = None
        raise ValueError('Expected header {} not found'.format(header))
