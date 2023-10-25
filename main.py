import os
import sys
from tkinter.messagebox import showinfo, showwarning
from PIL import Image, ImageTk
from queue import Queue, Empty
from threading import Thread, Lock

from modules.get_image import get_meta
from modules.settings import load_settings, SettingsWindow
from modules.stop_thread import stop_thread
from modules.popup_message import *


class MyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.progress_queue = Queue()  # 线程间消息传递
        self.version = "1.1"  # 程序版本
        self.settings = load_settings(self)  # 加载设置
        self.img_list = []  # 图片预加载列表&临时存放
        self.back_list = []  # 图片返回记录
        self.lock = Lock()  # 线程锁
        self.img_status = False  # 当前是否有图片，判断是否可以保存等
        self.thread_started = 0  # 当前开始的线程
        self.thread_list = []  # 存放线程的列表
        self.pic_wait = False  # 当正在获取的时候修改变量防止无限制多次请求
        self.create_widgets()
        self.create_menubar()
        self.after(1000, self.pic_resize)
        self.after(1, self.delete_messages)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        os.makedirs(self.settings.save_path.get(), exist_ok=True)

    def create_widgets(self):
        self.image_label = tk.Label(self)
        self.image_label.pack()
        self.image_label.bind("<Button- >", lambda *args: self.pic_info())
        initialize_popup(self.image_label)
        self.image_label.bind("<Enter>", lambda *args: show_popup(self.image_label, "点击图片或按下空格来显示图片信息"))
        self.image_label.bind("<Leave>", lambda *args: hide_popup(self.image_label))
        self.bind("<Key-space>", lambda *args: self.pic_info())
        self.button_frame = tk.Frame(self)
        self.button_frame.pack()
        self.back_button = tk.Button(self.button_frame, text="Back!(Right)", command=self.back_pic)
        self.back_button.pack(side=tk.LEFT)
        self.bind("<Key-Left>", lambda *args: self.back_pic())
        self.next_button = tk.Button(self.button_frame, text="Get!(Enter)", command=self.get_pic)
        self.bind("<Return>", lambda *args: self.get_pic())
        self.bind("<Key-Right>", lambda *args: self.get_pic())
        self.next_button.pack(side=tk.RIGHT)
        self.save_button = tk.Button(self.button_frame, text="Save!(S)", command=self.save_img)
        self.bind("<Key-s>", lambda *args: self.save_img())
        self.save_button.pack(side=tk.LEFT)

    def create_menubar(self):
        menu = tk.Menu(self)

        menu_editor = tk.Menu(self, tearoff=False)
        menu_editor.add_command(label="保存", command=self.save_img)
        menu_editor.add_command(label="获取", command=self.get_pic)
        menu.add_cascade(label="编辑", menu=menu_editor)

        menu_settings = tk.Menu(self, tearoff=False)
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

    def on_close(self):  # 程序关闭时等待子进程结束
        self.tp = tk.Toplevel(self)
        self.tp.geometry("200x40+%d+%d" % (self.winfo_x()+20, self.winfo_y()+20))
        tk.Label(self.tp, text="等待所有子线程关闭...").pack()
        self.tp.overrideredirect(True)
        self.delete_messages()
        for i in self.thread_list:
            stop_thread(i)
        self.after(1, self.really_close)

    def really_close(self):  # 当子进程全部结束后执行真正关闭窗口
        self.delete_messages()
        if self.thread_list:
            self.after(1, self.really_close)
        else:
            self.tp.destroy()
            self.destroy()
            exit(0)

    def get_pic(self):  # 分配获取图片的任务，同时尝试从缓存列表中提取下一张图片
        self.after(10, self.auto_distribute)
        if not self.pic_wait:  # 判断当前是否正在显示图片，如果没有图片则不尝试提取图片
            try:
                self.save_for_back(self.img_list.pop(0))
            except IndexError:
                pass
            self.after(1, self.pic_set)

    def save_for_back(self, imgfp):  # 对于经过的图片进行存放，便于程序返回上一张的时候进行查询
        if len(self.back_list) + 1 > self.settings.save_back.get():
            self.back_list.pop(0)[1].close()
        self.back_list.append(imgfp)

    def back_pic(self):
        try:
            self.img_list.insert(0, self.back_list.pop())
            self.pic_set()
        except IndexError:
            showwarning("警告", "没有上一张图片了\n你设置的历史缓存为%d张" % self.settings.save_back.get())

    def save_img(self):  # 保存当前图片
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
            frame.pack(fill=tk.BOTH, expand=tk.YES)
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
            text.pack(side="left", fill="both", expand=tk.YES)
            text.config(yscrollcommand=scroll.set)
            btn = tk.Button(pic_info_tp, text="确定(Enter)", command=pic_info_tp.destroy)
            pic_info_tp.bind("<Return>", lambda *args: pic_info_tp.destroy())
            pic_info_tp.bind("<Key-space>", lambda *args: pic_info_tp.destroy())
            pic_info_tp.bind("<FocusOut>", lambda *args: pic_info_tp.destroy())
            pic_info_tp.bind("<Key-Up>", lambda *args: text.yview_scroll(-1, "units"))
            pic_info_tp.bind("<Key-Down>", lambda *args: text.yview_scroll(1, "units"))
            pic_info_tp.bind("<Key-Prior>", lambda *args: text.yview_scroll(-1, "pages"))
            pic_info_tp.bind("<Key-Next>", lambda *args: text.yview_scroll(1, "pages"))
            btn.pack()
            pic_info_tp.wm_geometry("+%d+%d" % (self.winfo_x() + 20, self.winfo_y() + 20))
            pic_info_tp.focus_set()

    def pic_resize(self):  # 定时调用self.pic_set来使图片自适应窗口大小
        if self.img_status:
            self.pic_set()
        self.after(1000, self.pic_resize)

    def pic_set(self):  # 修改主Label，包括图片显示、子线程信息显示
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

    def auto_distribute(self):  # 调用即进行子线程释放，子线程多少取决于设置数量
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

    def delete_messages(self):  # 清除队列中无用信息，删除线程列表中无效线程
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


def main():
    app = MyApp()
    app.title(f"LSP Viewer v{app.version}")
    app.geometry("300x400+%d+%d" % (app.winfo_screenwidth() // 3, app.winfo_screenheight() // 3))
    app.mainloop()


if __name__ == "__main__":
    debug = os.environ.get("DEBUG")
    if not int(debug):
        console = sys.stdout
        f = open("log.txt", 'w')
        sys.stdout = f
        main()
        sys.stdout = console
        f.close()
    else:
        main()
