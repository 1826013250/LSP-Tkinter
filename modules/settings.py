import json
import os
import tkinter as tk
from tkinter import BooleanVar, StringVar, IntVar, Variable
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showwarning
from modules.stop_thread import stop_thread


class Settings:
    def __init__(
            self,
            master,
            r18=0,
            preload=0,
            exclude_ai=False,
            uid=None,
            tags=None,
            save_path="./out/"
    ):
        self.r18 = IntVar(master, r18)
        self.preload = IntVar(master, preload)
        self.exclude_ai = BooleanVar(master, exclude_ai)
        self.uid = Variable(value=[]) if not uid else Variable(value=uid)
        self.tags = Variable(value=[]) if not tags else Variable(value=tags)
        self.save_path = StringVar(master, save_path)


def dict2class(adict: dict, master):
    return Settings(
        r18=adict['r18'],
        master=master,
        preload=adict['preload'],
        exclude_ai=adict['exclude_ai'],
        uid=adict['uid'],
        tags=adict['tags'],
        save_path=adict['save_path']
    )


def class2dict(aclass: Settings):
    return {
        "r18": aclass.r18.get(),
        "preload": aclass.preload.get(),
        "exclude_ai": aclass.exclude_ai.get(),
        "uid": aclass.uid.get(),
        "tags": aclass.tags.get(),
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


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__()
        self.settings = master.settings
        self.master = master
        self.create_widgets()
        self.wm_title("设置")
        self.wm_geometry("300x330+%d+%d" % (master.winfo_x()+20, master.winfo_y()+20))
        self.wm_resizable(False, False)

    def create_widgets(self):
        r18_frame = tk.Frame(self)
        r18_frame.pack(fill="x")
        r18_label = tk.Label(r18_frame, text="R18图片状态")
        r18_label.pack(side="left")
        r18_rand = tk.Radiobutton(r18_frame, text="随机", value=2, variable=self.settings.r18)
        r18_rand.pack(side="right")
        r18_enable = tk.Radiobutton(r18_frame, text="仅R18", value=1, variable=self.settings.r18)
        r18_enable.pack(side="right")
        r18_disable = tk.Radiobutton(r18_frame, text="关", value=0, variable=self.settings.r18)
        r18_disable.pack(side="right")

        exclude_ai_frame = tk.Frame(self)
        exclude_ai_frame.pack(fill="x")
        exclude_ai_label = tk.Label(exclude_ai_frame, text="排除AI作品")
        exclude_ai_label.pack(side="left")
        exclude_ai_check = tk.Checkbutton(exclude_ai_frame, variable=self.settings.exclude_ai)
        exclude_ai_check.pack(side="right")

        def preload_validate():
            if preload_temp_var.get().isdigit():
                if int(preload_temp_var.get()) > 20:
                    self.settings.preload.set(20)
                    preload_temp_var.set("20")
                else:
                    self.settings.preload.set(int(preload_temp_var.get()))
                    preload_temp_var.set(self.settings.preload.get())
            elif not preload_temp_var.get():
                self.settings.preload.set(0)
                preload_temp_var.set("0")
            else:
                preload_temp_var.set(self.settings.preload.get())
            preload_entry.after(1, preload_validate)
        preload_temp_var = tk.StringVar(self, self.settings.preload.get())
        preload_frame = tk.Frame(self)
        preload_frame.pack(fill="x")
        preload_label = tk.Label(preload_frame, text="预加载图片数量")
        preload_label.pack(side="left")
        preload_entry = tk.Entry(preload_frame, textvariable=preload_temp_var, width=2)
        preload_entry.after(1, preload_validate)
        preload_entry.pack(side="right")

        path_frame = tk.Frame(self)
        path_frame.pack(fill="x")
        path_label = tk.Label(path_frame, text="图片保存路径")
        path_label.pack(side="left")
        path_btn = tk.Button(path_frame, text="选择...", command=lambda: self.settings.save_path.set(askdirectory()))
        path_btn.pack(side="right")
        path_entry = tk.Entry(path_frame, textvariable=self.settings.save_path, width=10)
        path_entry.pack(side="right")

        def add_tag_list(text="", first=tk.END):
            tp = tk.Toplevel(self)
            tp.geometry("300x80+%d+%d" % (self.winfo_x()+20, self.winfo_y()+20))
            tp.title("设置标签")
            tp.label = tk.Label(tp, text="请输入要检索的标签，用\"|\"标记其他可选项")
            tp.label.pack()
            tp.entry = tk.Entry(tp)
            tp.entry.insert(tk.END, text)
            tp.entry.pack(fill="x")
            tp.btn_frame = tk.Frame(tp)
            tp.btn_frame.pack()
            tp.btn_cancel = tk.Button(tp.btn_frame, text="取消", command=tp.destroy)
            tp.btn_confirm = tk.Button(tp.btn_frame, text="确定", command=lambda: (
                tags_list.insert(first, tp.entry.get()),
                tp.destroy()
            ) if first == tk.END else (
                tags_list.delete(first),
                tags_list.insert(first, tp.entry.get()),
                tp.destroy()
            ))
            tp.btn_cancel.pack(side="left")
            tp.btn_confirm.pack(side="right")

        def tag_del_selected():
            try:
                tags_list.delete(tags_list.curselection())
            except tk.TclError:
                pass

        def tag_modify_selected():
            try:
                add_tag_list(tags_list.get(tags_list.curselection()), tags_list.curselection())
            except tk.TclError:
                pass
        tags_frame = tk.Frame(self)
        tags_frame.pack(fill="x")
        tags_label = tk.Label(tags_frame, text="标签筛选")
        tags_label.pack(side="left")
        tags_btn_frame = tk.Frame(tags_frame)
        tags_btn_frame.pack(side="right")
        tags_btn_add = tk.Button(tags_btn_frame, text="添加", command=add_tag_list)
        tags_btn_mod = tk.Button(tags_btn_frame, text="编辑", command=tag_modify_selected)
        tags_btn_del = tk.Button(tags_btn_frame, text="删除", command=tag_del_selected)
        tags_btn_add.pack()
        tags_btn_mod.pack()
        tags_btn_del.pack()
        tags_list_frame = tk.Frame(tags_frame)
        tags_list_frame.pack(side="right")
        tags_scroll = tk.Scrollbar(tags_list_frame)
        tags_scroll.pack(side="right", fill="y")
        tags_list = tk.Listbox(tags_list_frame,
                               yscrollcommand=tags_scroll.set,
                               height=5, width=10,
                               listvariable=self.settings.tags)
        tags_scroll.config(command=tags_list.yview)
        tags_list.pack(side="right")

        def add_uid_list(text="", first=tk.END):
            tp = tk.Toplevel(self)
            tp.geometry("200x80+%d+%d" % (self.winfo_x()+20, self.winfo_y()+20))
            tp.title("设置作者uid")
            tp.label = tk.Label(tp, text="请输入作者的uid")
            tp.label.pack()
            tp.entry = tk.Entry(tp)
            tp.entry.insert(tk.END, text)
            tp.entry.pack(fill="x")
            tp.btn_frame = tk.Frame(tp)
            tp.btn_frame.pack()
            tp.btn_cancel = tk.Button(tp.btn_frame, text="取消", command=tp.destroy)
            tp.btn_confirm = tk.Button(tp.btn_frame, text="确定", command=lambda: (
                uid_list.insert(first, tp.entry.get()),
                tp.destroy()
            ) if first == tk.END and tp.entry.get().isdigit() else (
                uid_list.delete(first),
                uid_list.insert(first, tp.entry.get()),
                tp.destroy()
            ) if tp.entry.get().isdigit() else (
                showwarning("Warning", "作者uid中只能存在数字！")
            ))
            tp.btn_cancel.pack(side="left")
            tp.btn_confirm.pack(side="right")

        tk.Label(self).pack()

        def uid_modify_selected():
            try:
                add_uid_list(uid_list.get(uid_list.curselection()), uid_list.curselection())
            except tk.TclError:
                pass

        def uid_del_selected():
            try:
                uid_list.delete(uid_list.curselection())
            except tk.TclError:
                pass
        uid_frame = tk.Frame(self)
        uid_frame.pack(fill="x")
        uid_label = tk.Label(uid_frame, text="作者uid筛选")
        uid_label.pack(side="left")
        uid_btn_frame = tk.Frame(uid_frame)
        uid_btn_frame.pack(side="right")
        uid_btn_add = tk.Button(uid_btn_frame, text="添加", command=add_uid_list)
        uid_btn_mod = tk.Button(uid_btn_frame, text="编辑", command=uid_modify_selected)
        uid_btn_del = tk.Button(uid_btn_frame, text="删除", command=uid_del_selected)
        uid_btn_add.pack()
        uid_btn_mod.pack()
        uid_btn_del.pack()
        uid_list_frame = tk.Frame(uid_frame)
        uid_list_frame.pack(side="right")
        uid_scroll = tk.Scrollbar(uid_list_frame)
        uid_scroll.pack(side="right", fill="y")
        uid_list = tk.Listbox(uid_list_frame,
                              yscrollcommand=uid_scroll.set,
                              height=5, width=10,
                              listvariable=self.settings.uid)
        uid_scroll.config(command=uid_list.yview)
        uid_list.pack(side="right")

        button_frame = tk.Frame(self)
        button_frame.pack()
        cancel_btn = tk.Button(button_frame, text="取消", command=self.destroy)
        cancel_btn.pack(side="left")
        save_btn = tk.Button(button_frame, text="确定", command=self.save_settings)
        save_btn.pack(side="right")

    def save_settings(self):
        save_settings(self.settings)
        self.master.img_list.clear()
        for i in self.master.thread_list:
            stop_thread(i)
        self.destroy()
