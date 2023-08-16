import json
import os
from tkinter import BooleanVar, Variable, StringVar, IntVar


class Settings:
    def __init__(
            self,
            master,
            r18=0,
            preload=0,
            pre_download=True,
            exclude_ai=False,
            uuid=None,
            tag=None,
            save_path="./out/"
    ):
        self.r18 = IntVar(master, r18)
        self.preload = IntVar(master, preload)
        self.pre_download = BooleanVar(master, pre_download)
        self.exclude_ai = BooleanVar(master, exclude_ai)
        self.uuid = Variable(master, (lambda: [] if not uuid else uuid)())
        self.tag = Variable(master, (lambda: [] if not tag else tag)())
        self.save_path = StringVar(master, save_path)


def dict2class(adict: dict, master):
    return Settings(
        r18=adict['r18'],
        master=master,
        preload=adict['preload'],
        pre_download=adict['pre_download'],
        exclude_ai=adict['exclude_ai'],
        uuid=adict['uuid'],
        tag=adict['tag'],
        save_path=adict['save_path']
    )


def class2dict(aclass: Settings):
    return {
        "r18": aclass.r18.get(),
        "preload": aclass.preload.get(),
        "pre_download": aclass.pre_download.get(),
        "exclude_ai": aclass.exclude_ai.get(),
        "uuid": aclass.uuid.get(),
        "tag": aclass.tag.get(),
        "save_path": aclass.save_path.get()
    }


def load_settings(master):
    if os.path.exists("config.json"):
        f = open("config.json", 'r')
        try:
            settings = json.load(f, object_hook=lambda adict: dict2class(adict, master))
            f.close()
            return settings
        except json.JSONDecodeError or KeyError:
            f.close()
            settings = Settings(master)
            save_settings(settings)
            return settings
    else:
        f = open("config.json", 'w')
        settings = Settings(master)
        json.dump(settings, f, default=class2dict)
        return settings


def save_settings(settings):
    with open("config.json", 'w') as f:
        json.dump(settings, f, default=class2dict)
