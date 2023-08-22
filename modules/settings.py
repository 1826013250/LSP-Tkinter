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
            preload=5,
            exclude_ai=False,
            uid=None,
            tags=None,
            save_path="./out/",
            proxy="",
            custom_proxy=""
    ):
        self.r18 = IntVar(master, r18)
        self.preload = IntVar(master, preload)
        self.exclude_ai = BooleanVar(master, exclude_ai)
        self.uid = Variable(value=[]) if not uid else Variable(value=uid)
        self.tags = Variable(value=[]) if not tags else Variable(value=tags)
        self.save_path = StringVar(master, save_path)
        self.proxy = StringVar(master, proxy)
        self.custom_proxy = StringVar(master, custom_proxy)


def dict2class(adict: dict, master):
    return Settings(
        r18=adict['r18'],
        master=master,
        preload=adict['preload'],
        exclude_ai=adict['exclude_ai'],
        uid=adict['uid'],
        tags=adict['tags'],
        save_path=adict['save_path'],
        proxy=adict['proxy'],
        custom_proxy=adict['custom_proxy']
    )


def class2dict(aclass: Settings):
    return {
        "r18": aclass.r18.get(),
        "preload": aclass.preload.get(),
        "exclude_ai": aclass.exclude_ai.get(),
        "uid": aclass.uid.get(),
        "tags": aclass.tags.get(),
        "save_path": aclass.save_path.get(),
        "proxy": aclass.proxy.get(),
        "custom_proxy": aclass.custom_proxy.get()
    }


def load_settings(master):
    if os.path.exists("config.json"):
        f = open("config.json", 'r')
        try:
            settings = json.load(f, object_hook=lambda adict: dict2class(adict, master))
            f.close()
            return settings
        except (json.JSONDecodeError, KeyError):
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
        super().__init__(master)
        self.settings = master.settings
        self.proxy_temp_var = tk.IntVar(value=0 if not self.settings.proxy.get() else (
            1 if self.settings.proxy.get() == "pixiv.yuki.sh" else 2))
        self.create_widgets()
        self.wm_title("设置")
        self.wm_resizable(False, False)
        self.after(20, lambda *args: self.wm_geometry("%dx%d+%d+%d" % (self.winfo_width(),
                                                                       self.winfo_height(),
                                                                       master.winfo_x()+20,
                                                                       master.winfo_y()+20)))
        self.focus_set()
        self.wm_attributes("-topmost", 1)

    def create_folders(self):
        os.makedirs(self.settings.save_path, exist_ok=True)

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

        def set_dictionary():
            path = askdirectory()
            if path:
                self.settings.save_path.set()
        path_frame = tk.Frame(self)
        path_frame.pack(fill="x")
        path_label = tk.Label(path_frame, text="图片保存路径")
        path_label.pack(side="left")
        path_btn = tk.Button(path_frame, text="选择...", command=set_dictionary)
        path_btn.pack(side="right")
        path_entry = tk.Entry(path_frame, textvariable=self.settings.save_path, width=10)
        path_entry.pack(side="right")

        def add_tag_list(text="", first=tk.END):
            ToplevelInput(self, "设置标签", "请输入要检索的标签，用\"|\"来添加多个可选项", text, lambda tp: (
                tags_list.insert(tp.kwargs["first"], tp.entry.get()),
            ) if first == tk.END else (
                tags_list.delete(tp.kwargs["first"]),
                tags_list.insert(tp.kwargs["first"], tp.entry.get()),
            ), first=first)

        def tag_del_selected():
            now = tags_list.curselection()
            if now:
                now = now[0]
                now -= 1
                tags_list.delete(tags_list.curselection())
                if now >= 0:
                    tags_list.selection_set(now)
                else:
                    try:
                        if tags_list.get((0, )):
                            tags_list.selection_set(0)
                    except tk.TclError:
                        pass
            else:
                try:
                    if tags_list.get((0, )):
                        tags_list.delete(0)
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

        tk.Label(self).pack()

        def add_uid_list(text="", first=tk.END):
            ToplevelInput(self, "设置作者uid", "请输入作者uid", text, lambda tp: (
                uid_list.insert(tp.kwargs["first"], tp.entry.get()),
            ) if first == tk.END and tp.entry.get().isdigit() else (
                uid_list.delete(tp.kwargs["first"]),
                uid_list.insert(tp.kwargs["first"], tp.entry.get()),
            ) if tp.entry.get().isdigit() else (
                showwarning("Warning", "作者uid中只能存在数字！")
            ), first=first)

        def uid_modify_selected():
            try:
                add_uid_list(uid_list.get(uid_list.curselection()), uid_list.curselection())
            except tk.TclError:
                pass

        def uid_del_selected():
            now = uid_list.curselection()
            if now:
                now = now[0]
                now -= 1
                uid_list.delete(uid_list.curselection())
                if now >= 0:
                    uid_list.selection_set(now)
                else:
                    try:
                        if uid_list.get((0,)):
                            uid_list.selection_set(0)
                    except tk.TclError:
                        pass
            else:
                try:
                    if uid_list.get((0,)):
                        uid_list.delete(0)
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

        proxy_frame = tk.Label(self)
        proxy_frame.pack(fill="x")
        proxy_label = tk.Label(proxy_frame, text="Pixiv反代理")
        proxy_label.pack(side="left")
        proxy_custom_btn = tk.Button(proxy_frame,
                                     text="自定",
                                     command=lambda: ToplevelInput(
                                         self,
                                          "设置反代理",
                                          "请输入反代理网址(只保留主域名)",
                                          self.settings.custom_proxy.get(),
                                          lambda tp: self.settings.custom_proxy.set(tp.entry.get())
                                      ))
        proxy_custom_btn.pack(side="right")
        proxy_custom = tk.Radiobutton(proxy_frame,
                                      value=2,
                                      variable=self.proxy_temp_var,
                                      command=lambda: self.settings.proxy.set(self.settings.custom_proxy.get()))
        proxy_custom.pack(side="right")
        proxy_fallback = tk.Radiobutton(proxy_frame,
                                        text="备用",
                                        value=1,
                                        variable=self.proxy_temp_var,
                                        command=lambda: self.settings.proxy.set("pixiv.yuki.sh"))
        proxy_fallback.pack(side="right")
        proxy_main = tk.Radiobutton(proxy_frame,
                                    text="主要",
                                    value=0,
                                    variable=self.proxy_temp_var,
                                    command=lambda: self.settings.proxy.set(""))
        proxy_main.pack(side="right")

        final_button_frame = tk.Frame(self)
        final_button_frame.pack()
        final_cancel_btn = tk.Button(final_button_frame, text="取消", command=self.destroy)
        final_cancel_btn.pack(side="left")
        final_save_btn = tk.Button(final_button_frame, text="确定", command=self.save_settings)
        final_save_btn.pack(side="right")

    def save_settings(self):
        save_settings(self.settings)
        self.master.img_list.clear()
        for i in self.master.thread_list:
            stop_thread(i)
        self.destroy()


class ToplevelInput(tk.Toplevel):
    def __init__(self, master, title, label_text, entry_text, btn_command, **kwargs):
        super().__init__(master)
        self.wm_title(title)
        self.label_text = label_text
        self.entry_text = entry_text
        self.btn_command = btn_command
        self.kwargs = kwargs
        self.create_widgets()
        self.after(20, lambda *args: self.geometry("%dx%d+%d+%d" % (self.winfo_width(),
                                                                    self.winfo_height(),
                                                                    self.master.winfo_x() + 20,
                                                                    self.master.winfo_y() + 20)))
        self.master.wm_attributes("-topmost", 0)
        self.wm_attributes("-topmost", 1)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def close_window(self):
        self.master.wm_attributes("-topmost", 1)
        self.destroy()

    def create_widgets(self):
        label = tk.Label(self, text=self.label_text)
        label.pack()
        self.entry = tk.Entry(self)
        self.entry.insert(tk.END, self.entry_text)
        self.entry.pack(fill="x")
        btn_frame = tk.Frame(self)
        btn_frame.pack()
        btn_cancel = tk.Button(btn_frame, text="取消", command=self.close_window)
        btn_cancel.pack(side="left")
        btn_confirm = tk.Button(btn_frame, text="确定", command=lambda: (self.btn_command(self), self.close_window()))
        btn_confirm.pack(side="right")
        self.bind("<Return>", lambda *args: self.btn_command(self))
        self.deiconify()
        self.entry.focus_set()
