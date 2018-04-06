#!/usr/bin/env python3

from telegram import User


class TgMixin:
    @classmethod
    def get_or_create(cls, obj):
        if isinstance(obj, User):
            params = obj.to_dict()
        else:
            params = dict()
        o = cls.get(**params)
        if o:
            return o
        return cls(**params)