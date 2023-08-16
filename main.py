import tkinter as tk
import os
import inspect
import ctypes
from tkinter.messagebox import showinfo
from tkinter.filedialog import askdirectory
from PIL import Image, ImageTk
from queue import Queue
from threading import Thread, Lock
from io import BytesIO
from time import sleep

from get_image import getpic
from settings import load_settings, save_settings


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


class MyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.progress_queue = Queue()
        self.version = "0.0.0"
        self.settings = load_settings(self)
        self.img_list = []
        self.lock = Lock()
        self.img_status = False
        self.thread_started = 0
        self.thread_list = []
        self.pic_wait = False
        self.create_widgets()
        self.create_menubar()
        self.after(1000, self.pic_resize)
        self.after(10, self.auto_distribute)
        self.after(1, self.delete_messages)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        self.image_label = tk.Label(self)
        self.image_label.pack()

        self.button_frame = tk.Frame(self)
        self.button_frame.pack()
        self.next_button = tk.Button(self.button_frame, text="Get!(Enter)", command=self.get_pic)
        self.bind("<Return>", lambda *args: self.get_pic())
        self.next_button.pack(side="right")
        self.save_button = tk.Button(self.button_frame, text="Save!(S)", command=self.save_img)
        self.bind("<Key-s>", lambda *args: self.save_img())
        self.save_button.pack(side="left")

    def create_menubar(self):
        menu = tk.Menu(self)

        menueditor = tk.Menu(self)
        menueditor.add_command(label="保存", command=self.save_img)
        menueditor.add_command(label="获取", command=self.get_pic)
        menu.add_cascade(label="编辑", menu=menueditor)

        menusettings = tk.Menu(self)
        menusettings.add_command(label="打开设置", command=lambda: Settings(self.settings, self.winfo_x(), self.winfo_y()))
        menusettings.add_command(label="重置设置", command=...)
        menu.add_cascade(label="设置", menu=menusettings)

        self.config(menu=menu)

    def on_close(self):
        self.tp = tk.Toplevel(self)
        self.tp.geometry("200x40+%d+%d" % (self.winfo_x()+20, self.winfo_y()+20))
        tk.Label(self.tp, text="等待所有子线程关闭...").pack()
        self.tp.overrideredirect(True)
        self.delete_messages()
        for i in self.thread_list:
            stop_thread(i)
        self.after(1, self.really_close)

    def really_close(self):
        self.delete_messages()
        if self.thread_list:
            self.after(1, self.really_close)
        else:
            self.tp.destroy()
            self.destroy()
            exit(0)

    def get_pic(self):
        if not self.pic_wait:
            try:
                self.img_list.pop(0)
            except IndexError:
                pass
            self.after(1, self.pic_set)

    def save_img(self):
        if self.img_status:
            i = 0
            with open(os.path.join(self.settings.save_path.get(), f"{self.meta['pid']}.jpg"), 'wb') as f:
                f.write(self.rimg)
                showinfo("Success!",
                         "文件已保存!路径为：\n"
                         f"{os.path.join(self.settings.save_path.get(), '%s.jpg' % self.meta['pid'])}")
        else:
            showinfo("Oops!", "当前没有图片!")

    def pic_resize(self):
        if self.img_status:
            self.pic_set()
        self.after(1000, self.pic_resize)

    def pic_set(self):
        self.pic_wait = True
        if self.img_list:
            img = self.img_list[0]
            self.meta = img[0]
            self.rimg = img[1]
            self.simg = Image.open(BytesIO(self.rimg))
            w, h = self.simg.width, self.simg.height
            times = max(w/self.winfo_width(), h/self.winfo_height())
            self.simg.thumbnail((int(w/times), int(h/times-40)))
            self.simgtk = ImageTk.PhotoImage(self.simg)
            self.image_label.config(image=self.simgtk)
            self.img_status = True
            self.pic_wait = False
        else:
            self.img_status = False
            if not self.progress_queue.empty():
                self.image_label.config(text=self.progress_queue.get(), image="")
            self.after(1, self.pic_set)

    def auto_distribute(self):
        if len(self.img_list) + self.thread_started <= self.settings.preload.get():
            content = {
                "r18": self.settings.r18.get(),
                "tag": self.settings.tag.get(),
                "excludeAI": self.settings.exclude_ai.get()
            }
            thread = Thread(target=self.thread_work, args=[content, self.thread_started])
            thread.start()
            self.thread_list.append(thread)
            self.thread_started += 1
        self.after(100, self.auto_distribute)

    def thread_work(self, content, thread_id):
        print("Thread #%d Run!" % thread_id)
        self.progress_queue.put("线程#%d正在获取图片地址..." % thread_id)
        r = getpic(self.progress_queue, thread_id, content)
        if r == "error":
            self.progress_queue.put("线程#%d获取图片失败！" % thread_id)
        elif r == "not_found":
            self.progress_queue.put("线程#%d图片未找到,自动重新获取..." % thread_id)
        elif type(r) == tuple:
            self.lock.acquire()
            self.img_list.append(r)
            print("Thread #%d Added List" % thread_id)
            self.lock.release()
        print("Thread #%d Finish!" % thread_id)
        self.thread_started -= 1

    def delete_messages(self):
        if not self.pic_wait and not self.progress_queue.empty():
            self.progress_queue.get()
        dellist = []
        for i in range(len(self.thread_list)):
            if not self.thread_list[i].is_alive():
                dellist.append(i)
        for i in dellist:
            try:
                self.thread_list.pop(i)
            except IndexError:
                pass
        self.after(1, self.delete_messages)


class Settings(tk.Toplevel):
    def __init__(self, settings, x, y):
        super().__init__()
        self.settings = settings
        self.create_widgets()
        self.wm_title("设置")
        self.wm_geometry("300x200+%d+%d" % (x, y))
        self.wm_resizable(False, False)

    def create_widgets(self):
        r18frame = tk.Frame(self)
        r18frame.pack(fill="x")
        r18label = tk.Label(r18frame, text="R18图片状态")
        r18label.pack(side="left")
        r18rand = tk.Radiobutton(r18frame, text="随机", value=2, variable=self.settings.r18)
        r18rand.pack(side="right")
        r18enable = tk.Radiobutton(r18frame, text="仅R18", value=1, variable=self.settings.r18)
        r18enable.pack(side="right")
        r18disable = tk.Radiobutton(r18frame, text="关", value=0, variable=self.settings.r18)
        r18disable.pack(side="right")

        excaiframe = tk.Frame(self)
        excaiframe.pack(fill="x")
        excailabel = tk.Label(excaiframe, text="排除AI作品")
        excailabel.pack(side="left")
        excaicheck = tk.Checkbutton(excaiframe, variable=self.settings.exclude_ai)
        excaicheck.pack(side="right")

        prednframe = tk.Frame(self)
        prednframe.pack(fill="x")
        prednlabel = tk.Label(prednframe, text="预下载当前图片")
        prednlabel.pack(side="left")
        predncheck = tk.Checkbutton(prednframe, variable=self.settings.pre_download)
        predncheck.pack(side="right")

        def preload_validate():
            if preload_tempvar.get().isdigit():
                self.settings.preload.set(int(preload_tempvar.get()))
                preload_tempvar.set(self.settings.preload.get())
            elif not preload_tempvar.get():
                self.settings.preload.set(0)
                preload_tempvar.set("0")
            else:
                preload_tempvar.set(self.settings.preload.get())
            preloadentry.after(1, preload_validate)
        preload_tempvar = tk.StringVar(self, self.settings.preload.get())
        preloadframe = tk.Frame(self)
        preloadframe.pack(fill="x")
        preloadlabel = tk.Label(preloadframe, text="预加载图片数量")
        preloadlabel.pack(side="left")
        preloadentry = tk.Entry(preloadframe, textvariable=preload_tempvar, width=2)
        preloadentry.after(1, preload_validate)
        preloadentry.pack(side="right")

        pathframe = tk.Frame(self)
        pathframe.pack(fill="x")
        pathlabel = tk.Label(pathframe, text="图片保存路径")
        pathlabel.pack(side="left")
        pathbtn = tk.Button(pathframe, text="选择...", command=lambda: self.settings.save_path.set(askdirectory()))
        pathbtn.pack(side="right")
        pathentry = tk.Entry(pathframe, textvariable=self.settings.save_path)
        pathentry.pack(side="right")

        buttonframe = tk.Frame(self)
        buttonframe.pack(fill="x")
        cancelbtn = tk.Button(buttonframe, text="取消", command=self.destroy)
        cancelbtn.pack(side="left")
        savebtn = tk.Button(buttonframe, text="确定", command=self.save_settings)
        savebtn.pack(side="right")

    def save_settings(self):
        save_settings(self.settings)
        self.destroy()


if __name__ == "__main__":
    app = MyApp()
    app.title(f"LSP Viewer v{app.version}")
    app.geometry("300x400")
    app.mainloop()
