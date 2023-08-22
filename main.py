import tkinter as tk
import os
from tkinter.messagebox import showinfo
from PIL import Image, ImageTk
from queue import Queue, Empty
from threading import Thread, Lock

from modules.get_image import get_meta
from modules.settings import load_settings, SettingsWindow
from modules.stop_thread import stop_thread


class MyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.progress_queue = Queue()
        self.version = "1.0"
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
        self.after(1, self.delete_messages)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        self.image_label = tk.Label(self)
        self.image_label.pack()
        self.image_label.bind("<Button- >", lambda *args: self.pic_info())
        self.bind("<Key- >", lambda *args: self.pic_info())
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

        menu_editor = tk.Menu(self)
        menu_editor.add_command(label="保存", command=self.save_img)
        menu_editor.add_command(label="获取", command=self.get_pic)
        menu.add_cascade(label="编辑", menu=menu_editor)

        menu_settings = tk.Menu(self)
        menu_settings.add_command(label="打开设置", command=lambda: SettingsWindow(self))
        menu_settings.add_command(label="重置设置", command=self.reset_config)
        menu.add_cascade(label="设置", menu=menu_settings)

        self.config(menu=menu)

    def reset_config(self):
        try:
            os.remove("config.json")
        except FileNotFoundError:
            pass
        self.settings = load_settings(self)

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
        self.after(10, self.auto_distribute)
        if not self.pic_wait:
            try:
                self.img_list.pop(0)[1].close()
                self.imgfp.close()
            except IndexError:
                pass
            self.after(1, self.pic_set)

    def save_img(self):
        if self.img_status:
            with open(os.path.join(self.settings.save_path.get(), f"{self.meta['pid']}.{self.meta['ext']}"), 'wb') as f:
                self.imgfp.seek(0)
                f.write(self.imgfp.read())
                showinfo("Success!",
                         "文件已保存!路径为：\n"
                         f"{os.path.join(self.settings.save_path.get(), '%s.jpg' % self.meta['pid'])}")
        else:
            showinfo("Oops!", "当前没有图片!")

    def pic_info(self):
        if self.img_status:
            pic_info_tp = tk.Toplevel(self)
            pic_info_tp.title("当前图片信息")
            frame = tk.Frame(pic_info_tp, width=100, height=300)
            frame.pack()
            text = tk.Text(frame, relief=tk.SUNKEN, width=30)
            scroll = tk.Scrollbar(frame, command=text.yview)
            scroll.pack(side="right", fill="y")
            text.insert("0.0", f"""作品名称:
{self.meta["title"]}

作品pid:
{self.meta["pid"]}

作者:
{self.meta["author"]}

作者uid:
{self.meta["uid"]}

AI绘图:
{["未知", "不是", "是"][self.meta["aiType"]]}

API分类R18:
{["不是", "是"][int(self.meta["r18"])]}

图片Tag R-18:
%s

作品标签:
%s

原图链接:
{self.meta["urls"]["original"]}
""" % ("是" if "R-18" in self.meta["tags"] else "不是", "\n".join(self.meta["tags"])))
            text.config(state="disabled")
            text.pack(side="left", fill="both")
            text.config(yscrollcommand=scroll.set)
            btn = tk.Button(pic_info_tp, text="确定(Enter)", command=pic_info_tp.destroy)
            pic_info_tp.bind("<Return>", lambda *args: pic_info_tp.destroy())
            pic_info_tp.bind("<Key- >", lambda *args: pic_info_tp.destroy())
            pic_info_tp.bind("<FocusOut>", lambda *args: pic_info_tp.destroy())
            btn.pack()
            pic_info_tp.after(5, lambda: pic_info_tp.geometry("%dx%d+%d+%d" % (pic_info_tp.winfo_width(),
                                                                               pic_info_tp.winfo_height(),
                                                                               self.winfo_x() + 20,
                                                                               self.winfo_y() + 20)))
            pic_info_tp.deiconify()

    def pic_resize(self):
        if self.img_status:
            self.pic_set()
        self.after(1000, self.pic_resize)

    def pic_set(self):
        self.pic_wait = True
        if self.img_list:
            img = self.img_list[0]
            self.meta = img[0]
            self.imgfp = img[1]
            self.simg = Image.open(self.imgfp)
            w, h = self.simg.width, self.simg.height
            times = max(w/self.winfo_width(), h/self.winfo_height())
            self.simg.thumbnail((int(w/times), int(h/times-40)))
            self.simgtk = ImageTk.PhotoImage(self.simg)
            self.image_label.config(image=self.simgtk)
            self.img_status = True
            self.pic_wait = False
        else:
            self.img_status = False
            try:
                while True:
                    self.image_label.config(text=self.progress_queue.get_nowait(), image="")
            except Empty:
                pass
            self.after(1, self.pic_set)

    def auto_distribute(self):
        if len(self.img_list) + self.thread_started <= self.settings.preload.get():
            content = {
                "r18": self.settings.r18.get(),
                "tag": self.settings.tags.get(),
                "uid": list(map(int, self.settings.uid.get())),
                "excludeAI": self.settings.exclude_ai.get(),
                "proxy": self.settings.proxy.get()
            }
            thread = Thread(target=self.thread_work, args=[content, self.thread_started])
            thread.start()
            self.thread_list.append(thread)
            self.thread_started += 1
            self.after(10, self.auto_distribute)

    def thread_work(self, content, thread_id):
        print("Thread #%d Run!" % thread_id)
        self.lock.acquire()
        self.progress_queue.put("线程#%d正在获取图片地址..." % thread_id)
        self.lock.release()
        r = get_meta(self.progress_queue, thread_id, content)
        if r == "error_pic":
            self.lock.acquire()
            self.progress_queue.put("线程#%d获取图片失败！请尝试更换Pixiv反代理" % thread_id)
            self.lock.release()
        elif r == "error_meta":
            self.lock.acquire()
            self.progress_queue.put("线程#%d获取链接失败！" % thread_id)
            self.lock.release()
        elif r == "not_found":
            self.lock.acquire()
            self.progress_queue.put("线程#%d图片未找到!" % thread_id)
            self.lock.release()
        elif type(r) == tuple:
            self.lock.acquire()
            self.img_list.append(r)
            print("Thread #%d Added List" % thread_id)
            self.lock.release()
        print("Thread #%d Finish!" % thread_id)
        self.thread_started -= 1

    def delete_messages(self):
        if not self.pic_wait:
            while True:
                try:
                    self.progress_queue.get_nowait()
                except Empty:
                    break
        del_list = []
        for i in range(len(self.thread_list)):
            if not self.thread_list[i].is_alive():
                del_list.append(i)
        for i in reversed(del_list):
            try:
                self.thread_list.pop(i)
            except IndexError:
                pass
        self.after(1, self.delete_messages)


if __name__ == "__main__":
    app = MyApp()
    app.title(f"LSP Viewer v{app.version}")
    app.geometry("300x400+%d+%d" % (app.winfo_screenwidth() // 3, app.winfo_screenheight() // 3))
    app.mainloop()
