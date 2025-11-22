#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows定时电源管理工具 - 支持系统托盘
支持定时关机、睡眠、休眠功能
支持倒计时和指定时间点两种模式
支持最小化到系统托盘后台运行
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys
from datetime import datetime, timedelta
import pystray
from PIL import Image, ImageDraw
import queue


class PowerScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows定时电源管理工具")
        self.root.geometry("450x520")
        self.root.resizable(False, False)

        # 设置窗口图标和关闭行为
        self.setup_window_behavior()

        self.timer_thread = None
        self.is_running = False
        self.cancel_flag = False
        self.target_time = None
        self.icon = None

        # 用于线程间通信的队列
        self.update_queue = queue.Queue()

        self.setup_ui()

    def setup_window_behavior(self):
        """设置窗口行为"""
        # 设置窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 设置窗口图标
        try:
            self.root.iconbitmap('default')
        except:
            pass

    def create_icon(self):
        """创建托盘图标"""
        # 创建一个简单的圆形图标
        image = Image.new('RGB', (64, 64), color = 'white')
        draw = ImageDraw.Draw(image)

        # 绘制一个简单的电源符号
        draw.ellipse([8, 8, 56, 56], outline='blue', width=3)
        draw.line([32, 16, 32, 32], fill='blue', width=3)
        draw.arc([20, 20, 44, 44], start=0, end=180, fill='blue', width=3)

        return image

    def on_close(self):
        """窗口关闭事件处理"""
        if self.is_running:
            # 如果正在运行定时，隐藏到托盘而不是关闭
            self.hide_to_tray()
            messagebox.showinfo("提示", "程序已最小化到系统托盘，定时任务继续运行。\n\n双击托盘图标可重新打开窗口，\n右键托盘图标可选择完全退出。")
        else:
            # 如果没有运行定时，直接关闭
            if self.icon:
                self.icon.stop()
            self.root.quit()
            sys.exit()

    def hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        self.root.withdraw()

        # 如果托盘图标不存在，创建它
        if not self.icon:
            self.create_tray_icon()

    def create_tray_icon(self):
        """创建系统托盘图标"""
        def show_window(icon, item):
            """显示主窗口"""
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        def quit_app(icon, item):
            """完全退出应用程序"""
            self.is_running = False
            self.cancel_flag = True
            self.icon.stop()
            self.root.quit()
            sys.exit()

        def get_status():
            """获取当前状态，用于托盘菜单"""
            if self.is_running:
                if self.target_time:
                    remaining = self.target_time - datetime.now()
                    if remaining.total_seconds() > 0:
                        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        action_name = self.get_action_name()
                        return f"{action_name}中 ({hours:02d}:{minutes:02d}:{seconds:02d})"
                    else:
                        return "即将执行"
                else:
                    return "运行中"
            else:
                return "待机中"

        # 动态创建菜单
        def create_menu():
            status = get_status()
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", show_window, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(status, lambda icon, item: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", quit_app)
            )
            return menu

        # 创建图标
        self.icon = pystray.Icon(
            "power_scheduler",
            self.create_icon(),
            "定时电源管理工具",
            create_menu()
        )

        # 在单独线程中运行托盘
        threading.Thread(target=self.icon.run, daemon=True).start()

        # 定期更新托盘菜单
        self.update_tray_menu()

    def update_tray_menu(self):
        """定期更新托盘菜单"""
        try:
            if self.icon and self.icon.visible:
                self.icon.menu = self.create_tray_menu()
        except:
            pass

        # 每3秒更新一次
        self.root.after(3000, self.update_tray_menu)

    def create_tray_menu(self):
        """创建托盘菜单"""
        if self.is_running:
            if self.target_time:
                remaining = self.target_time - datetime.now()
                if remaining.total_seconds() > 0:
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    action_name = self.get_action_name()
                    status_text = f"{action_name}中 ({hours:02d}:{minutes:02d}:{seconds:02d})"
                else:
                    status_text = "即将执行"
            else:
                status_text = "运行中"
        else:
            status_text = "待机中"

        def show_window(icon, item):
            """显示主窗口"""
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        def quit_app(icon, item):
            """完全退出应用程序"""
            self.is_running = False
            self.cancel_flag = True
            if self.icon:
                self.icon.stop()
            self.root.quit()
            sys.exit()

        return pystray.Menu(
            pystray.MenuItem("显示窗口", show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(status_text, lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", quit_app)
        )

    def setup_ui(self):
        """设置用户界面"""
        # 电源操作选择框架
        action_frame = ttk.LabelFrame(self.root, text="选择电源操作", padding=10)
        action_frame.pack(fill="x", padx=10, pady=10)

        self.action_var = tk.StringVar(value="hibernate")

        actions = [
            ("休眠 (Hibernate)", "hibernate", "保存当前状态到硬盘，完全断电，恢复速度较慢但最省电"),
            ("睡眠 (Sleep)", "sleep", "保存当前状态到内存，低功耗待机，恢复速度快"),
            ("关机 (Shutdown)", "shutdown", "完全关闭系统，需要重新开机")
        ]

        for text, value, tooltip in actions:
            rb = ttk.Radiobutton(
                action_frame,
                text=text,
                variable=self.action_var,
                value=value
            )
            rb.pack(anchor="w", pady=2)
            # 添加工具提示（简单实现）
            self.create_tooltip(rb, tooltip)

        # 创建分隔线
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=10, pady=5)

        # 时间模式选择框架
        mode_frame = ttk.LabelFrame(self.root, text="选择时间模式", padding=10)
        mode_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="countdown")

        countdown_radio = ttk.Radiobutton(
            mode_frame,
            text="倒计时模式（从现在开始计时）",
            variable=self.mode_var,
            value="countdown",
            command=self.on_mode_change
        )
        countdown_radio.pack(anchor="w")

        scheduled_radio = ttk.Radiobutton(
            mode_frame,
            text="定时模式（设置具体时间点）",
            variable=self.mode_var,
            value="scheduled",
            command=self.on_mode_change
        )
        scheduled_radio.pack(anchor="w")

        # 倒计时设置框架
        self.countdown_frame = ttk.LabelFrame(self.root, text="设置倒计时时间", padding=10)
        self.countdown_frame.pack(fill="x", padx=10, pady=5)

        time_input_frame = ttk.Frame(self.countdown_frame)
        time_input_frame.pack()

        ttk.Label(time_input_frame, text="小时:").grid(row=0, column=0, padx=5)
        self.hours_var = tk.StringVar(value="0")
        hours_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=23, width=5, textvariable=self.hours_var)
        hours_spinbox.grid(row=0, column=1, padx=5)

        ttk.Label(time_input_frame, text="分钟:").grid(row=0, column=2, padx=5)
        self.minutes_var = tk.StringVar(value="30")
        minutes_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=59, width=5, textvariable=self.minutes_var)
        minutes_spinbox.grid(row=0, column=3, padx=5)

        ttk.Label(time_input_frame, text="秒:").grid(row=0, column=4, padx=5)
        self.seconds_var = tk.StringVar(value="0")
        seconds_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=59, width=5, textvariable=self.seconds_var)
        seconds_spinbox.grid(row=0, column=5, padx=5)

        # 定时设置框架
        self.scheduled_frame = ttk.LabelFrame(self.root, text="设置执行时间点", padding=10)
        # 默认隐藏，只在定时模式下显示
        # self.scheduled_frame.pack(fill="x", padx=10, pady=5)

        time_scheduled_frame = ttk.Frame(self.scheduled_frame)
        time_scheduled_frame.pack()

        ttk.Label(time_scheduled_frame, text="时:").grid(row=0, column=0, padx=5)
        self.scheduled_hours_var = tk.StringVar(value="23")
        scheduled_hours_spinbox = ttk.Spinbox(time_scheduled_frame, from_=0, to=23, width=5, textvariable=self.scheduled_hours_var)
        scheduled_hours_spinbox.grid(row=0, column=1, padx=5)

        ttk.Label(time_scheduled_frame, text="分:").grid(row=0, column=2, padx=5)
        self.scheduled_minutes_var = tk.StringVar(value="0")
        scheduled_minutes_spinbox = ttk.Spinbox(time_scheduled_frame, from_=0, to=59, width=5, textvariable=self.scheduled_minutes_var)
        scheduled_minutes_spinbox.grid(row=0, column=3, padx=5)

        ttk.Label(time_scheduled_frame, text="（24小时制）").grid(row=0, column=4, padx=5)

        # 状态显示框架
        status_frame = ttk.LabelFrame(self.root, text="运行状态", padding=8)
        status_frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="未启动", font=("Arial", 11))
        self.status_label.pack(pady=3)

        self.countdown_label = ttk.Label(status_frame, text="", font=("Arial", 16, "bold"), foreground="blue")
        self.countdown_label.pack(pady=3)

        self.target_time_label = ttk.Label(status_frame, text="", font=("Arial", 9), foreground="gray")
        self.target_time_label.pack(pady=1)

        # 提示信息
        tip_label = ttk.Label(status_frame, text="💡 关闭窗口会最小化到托盘，定时任务继续运行",
                              font=("Arial", 8), foreground="green")
        tip_label.pack(pady=2)

        # 按钮框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)

        self.start_button = ttk.Button(button_frame, text="启动定时", command=self.start_timer)
        self.start_button.pack(side="left", expand=True, fill="x", padx=5)

        self.cancel_button = ttk.Button(button_frame, text="取消定时", command=self.cancel_timer, state="disabled")
        self.cancel_button.pack(side="left", expand=True, fill="x", padx=5)

        # 初始化显示
        self.on_mode_change()

    def create_tooltip(self, widget, text):
        """创建简单的工具提示"""
        def on_enter(event):
            widget.tooltip = tk.Toplevel()
            widget.tooltip.wm_overrideredirect(True)
            widget.tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(widget.tooltip, text=text, background="#ffffe0",
                           relief="solid", borderwidth=1, font=("Arial", 9))
            label.pack()

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')

        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

    def on_mode_change(self):
        """当模式改变时更新界面"""
        if self.mode_var.get() == "countdown":
            self.countdown_frame.pack(fill="x", padx=10, pady=5)
            self.scheduled_frame.pack_forget()
        else:
            self.countdown_frame.pack_forget()
            self.scheduled_frame.pack(fill="x", padx=10, pady=5)

    def get_action_name(self):
        """获取操作名称"""
        action_names = {
            "hibernate": "休眠",
            "sleep": "睡眠",
            "shutdown": "关机"
        }
        return action_names.get(self.action_var.get(), "操作")

    def start_timer(self):
        """启动定时器"""
        if self.is_running:
            messagebox.showwarning("警告", "定时器已在运行中！")
            return

        try:
            if self.mode_var.get() == "countdown":
                hours = int(self.hours_var.get())
                minutes = int(self.minutes_var.get())
                seconds = int(self.seconds_var.get())
                total_seconds = hours * 3600 + minutes * 60 + seconds

                if total_seconds <= 0:
                    messagebox.showerror("错误", "请设置有效的倒计时时间！")
                    return

                self.target_time = datetime.now() + timedelta(seconds=total_seconds)

                time_parts = []
                if hours > 0:
                    time_parts.append(f"{hours}小时")
                if minutes > 0:
                    time_parts.append(f"{minutes}分钟")
                if seconds > 0:
                    time_parts.append(f"{seconds}秒")
                mode_text = "".join(time_parts) + "后"

            else:  # scheduled mode
                scheduled_hours = int(self.scheduled_hours_var.get())
                scheduled_minutes = int(self.scheduled_minutes_var.get())

                now = datetime.now()
                self.target_time = now.replace(hour=scheduled_hours, minute=scheduled_minutes, second=0, microsecond=0)

                # 如果目标时间已过，设置为明天
                if self.target_time <= now:
                    self.target_time += timedelta(days=1)
                    day_text = "明天"
                else:
                    day_text = "今天"

                mode_text = f"{day_text} {scheduled_hours:02d}:{scheduled_minutes:02d}"

            # 启动定时器线程
            self.is_running = True
            self.cancel_flag = False
            self.start_button.config(state="disabled")
            self.cancel_button.config(state="normal")

            action_name = self.get_action_name()
            self.status_label.config(text=f"已启动 - 将在{mode_text}执行{action_name}")
            self.target_time_label.config(text=f"目标时间: {self.target_time.strftime('%Y-%m-%d %H:%M:%S')}")

            self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
            self.timer_thread.start()

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")

    def run_timer(self):
        """定时器运行线程"""
        while not self.cancel_flag and datetime.now() < self.target_time:
            remaining = self.target_time - datetime.now()

            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)

            countdown_text = f"剩余时间：{hours:02d}:{minutes:02d}:{seconds:02d}"

            # 更新UI（需要在主线程中执行）
            self.root.after(0, self.update_countdown, countdown_text)

            time.sleep(1)

        if not self.cancel_flag:
            # 时间到，执行操作
            self.root.after(0, self.execute_action)
        else:
            # 用户取消
            self.root.after(0, self.reset_ui)

    def update_countdown(self, text):
        """更新倒计时显示"""
        self.countdown_label.config(text=text)

    def execute_action(self):
        """执行电源操作"""
        action_name = self.get_action_name()

        # 直接执行操作，不需要确认
        # 执行相应的Windows命令
        action = self.action_var.get()
        if action == "hibernate":
            os.system("shutdown /h")
        elif action == "sleep":
            # Windows睡眠命令
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif action == "shutdown":
            os.system("shutdown /s /t 0")

    def cancel_timer(self):
        """取消定时器"""
        if self.is_running:
            self.cancel_flag = True
            self.is_running = False
            action_name = self.get_action_name()
            messagebox.showinfo("已取消", f"定时{action_name}已取消")
            self.reset_ui()

    def reset_ui(self):
        """重置界面"""
        self.is_running = False
        self.cancel_flag = False
        self.target_time = None
        self.status_label.config(text="未启动")
        self.countdown_label.config(text="")
        self.target_time_label.config(text="")
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")


def main():
    # 检查是否为Windows系统
    if sys.platform != "win32":
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", "此工具仅支持Windows系统！")
        return

    root = tk.Tk()
    app = PowerScheduler(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        if app.icon:
            app.icon.stop()
        sys.exit()


if __name__ == "__main__":
    main()
