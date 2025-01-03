import tkinter as tk
from tkinter import ttk, messagebox
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

        # Store current processes
        self.current_processes = set()
        
        # Create button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=1, column=0, columnspan=2, pady=5)

        # End Process button
        self.end_button = ttk.Button(self.button_frame, text="End Process", command=self.end_process)
        self.end_button.pack(side=tk.LEFT, padx=5)

        # Refresh button
        self.refresh_button = ttk.Button(self.button_frame, text="Refresh", command=self.refresh_processes)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        # Start monitoring
        self.running = True
        self.initial_scan()
        self.start_process_monitor()

    def initial_scan(self):
        """Perform initial scan of processes"""
        self.single_scan()
        # Store current PIDs
        self.current_processes = set(proc.pid for proc in psutil.process_iter())

    def start_process_monitor(self):
        """Start the background monitoring thread"""
        self.monitor_thread = threading.Thread(target=self.monitor_processes)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def monitor_processes(self):
        """Monitor for new processes in the background"""
        while self.running:
            try:
                # Get current set of processes
                new_processes = set(proc.pid for proc in psutil.process_iter())
                
                # Check if there are any changes
                if new_processes != self.current_processes:
                    # Update the process list
                    self.current_processes = new_processes
                    # Schedule the update in the main thread
                    self.after(0, self.single_scan)
                
                # Sleep for a short time before next check
                time.sleep(1)
            except:
                # Handle any errors silently and continue monitoring
                pass

    def single_scan(self):
        """Scan and update the process list"""
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

    def refresh_processes(self):
        """Manual refresh button handler"""
        self.single_scan()
        # Update current processes set
        self.current_processes = set(proc.pid for proc in psutil.process_iter())

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
        """Clean up when closing the window"""
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = ProcessWidget()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 