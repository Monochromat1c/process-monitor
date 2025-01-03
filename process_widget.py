import tkinter as tk
from tkinter import ttk
import psutil
import threading
import time

class ProcessWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        # Configure the window
        self.title("Process Monitor")
        self.attributes('-topmost', True)  # Keep widget on top
        self.resizable(False, False)

        # Style configuration
        style = ttk.Style()
        style.configure("Treeview", font=('Arial', 9))
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))

        # Create main frame
        self.main_frame = ttk.Frame(self, padding="5")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create treeview
        self.tree = ttk.Treeview(self.main_frame, columns=('PID', 'Memory'), height=15)
        self.tree.heading('#0', text='Process Name')
        self.tree.heading('PID', text='PID')
        self.tree.heading('Memory', text='Memory (MB)')
        
        # Configure column widths
        self.tree.column('#0', width=150)
        self.tree.column('PID', width=70)
        self.tree.column('Memory', width=100)
        
        self.tree.grid(row=0, column=0, columnspan=2)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Create button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=1, column=0, columnspan=2, pady=5)

        # End Process button
        self.end_button = ttk.Button(self.button_frame, text="End Process", command=self.end_process)
        self.end_button.pack(side=tk.LEFT, padx=5)

        # Replace Pause button with Refresh button
        self.refresh_button = ttk.Button(self.button_frame, text="Refresh", command=self.refresh_processes)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        # Start update thread with single scan
        self.running = True
        self.update_thread = threading.Thread(target=self.single_scan)
        self.update_thread.daemon = True
        self.update_thread.start()

    def refresh_processes(self):
        # Create new thread for each refresh to prevent GUI freezing
        refresh_thread = threading.Thread(target=self.single_scan)
        refresh_thread.daemon = True
        refresh_thread.start()

    def single_scan(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get and sort processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                process_info = proc.info
                memory_mb = process_info['memory_info'].rss / (1024 * 1024)
                processes.append((process_info['name'], process_info['pid'], memory_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort by memory usage (descending)
        processes.sort(key=lambda x: x[2], reverse=True)

        # Update treeview
        for proc in processes:
            self.tree.insert('', 'end', text=proc[0], values=(proc[1], f"{proc[2]:.1f}"))

    def end_process(self):
        selected_item = self.tree.selection()
        if selected_item:
            pid = int(self.tree.item(selected_item)['values'][0])
            try:
                psutil.Process(pid).terminate()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                tk.messagebox.showerror("Error", "Access denied to terminate this process")

    def on_closing(self):
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = ProcessWidget()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 