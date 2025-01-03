import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import threading
import time
import win32gui
import win32con
import win32api
import win32process
from PIL import Image, ImageTk
import os
import win32ui

class ProcessWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        # Configure the window
        self.title("Process Monitor")
        self.resizable(False, False)
        self.configure(bg='#f0f0f0')  # Light gray background
        
        # Center the window but align title to left
        self.option_add('*Dialog.msg.justify', 'left')
        self.option_add('*Dialog.msg.anchor', 'w')

        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')  # Use clam theme for modern look
        
        # Configure Treeview style
        style.configure("Treeview",
                       background="#ffffff",
                       fieldbackground="#ffffff",
                       foreground="#333333",
                       font=('Segoe UI', 9),
                       rowheight=25)
        
        style.configure("Treeview.Heading",
                       background="#e1e1e1",
                       foreground="#333333",
                       font=('Segoe UI', 10, 'bold'),
                       relief="flat")
        
        style.map("Treeview.Heading",
                 background=[('active', '#d1d1d1')])
        
        # Configure Button style
        style.configure("Custom.TButton",
                       background="#4a90e2",
                       foreground="#ffffff",
                       padding=(15, 5),
                       font=('Segoe UI', 9))
        
        style.map("Custom.TButton",
                 background=[('active', '#357abd')],
                 relief=[('pressed', 'sunken')])

        # Create main frame with padding and background
        self.main_frame = ttk.Frame(self, padding="10", style="Main.TFrame")
        style.configure("Main.TFrame", background='#f0f0f0')
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Store icons cache
        self.icon_cache = {}

        # Create treeview with adjusted height and selection colors
        self.tree = ttk.Treeview(self.main_frame, columns=('Name', 'PID', 'Memory'), height=15,
                                selectmode="browse")
        self.tree.heading('#0', text='')  # Icon column
        self.tree.heading('Name', text='Process Name')
        self.tree.heading('PID', text='PID')
        self.tree.heading('Memory', text='Memory (MB)')
        
        # Configure column widths
        self.tree.column('#0', width=45, stretch=False)  # Increased padding for icons
        self.tree.column('Name', width=200, stretch=True)
        self.tree.column('PID', width=80, stretch=False)
        self.tree.column('Memory', width=100, stretch=False)
        
        self.tree.grid(row=0, column=0, columnspan=2, padx=2, pady=(0, 10))

        # Style the scrollbar
        style.configure("Custom.Vertical.TScrollbar",
                       background="#4a90e2",
                       arrowcolor="#ffffff",
                       troughcolor="#f0f0f0")

        # Add scrollbar with custom style
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL,
                                command=self.tree.yview,
                                style="Custom.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S), padx=(0, 2))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Store current processes
        self.current_processes = set()
        
        # Create button and slider frame
        self.control_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.control_frame.grid(row=1, column=0, columnspan=2, pady=5)

        # Button frame for existing buttons
        self.button_frame = ttk.Frame(self.control_frame, style="Main.TFrame")
        self.button_frame.pack(side=tk.LEFT, padx=(0, 10))

        # End Process button with custom style
        self.end_button = ttk.Button(self.button_frame, text="End Process",
                                   command=self.end_process,
                                   style="Custom.TButton")
        self.end_button.pack(side=tk.LEFT, padx=5)

        # Refresh button with custom style
        self.refresh_button = ttk.Button(self.button_frame, text="Refresh",
                                       command=self.refresh_processes,
                                       style="Custom.TButton")
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        # Transparency control frame
        self.transparency_frame = ttk.Frame(self.control_frame, style="Main.TFrame")
        self.transparency_frame.pack(side=tk.LEFT)

        # Transparency label
        self.transparency_label = ttk.Label(self.transparency_frame, text="Opacity:",
                                          style="Main.TLabel")
        self.transparency_label.pack(side=tk.LEFT, padx=(0, 5))

        # Transparency slider
        self.transparency_var = tk.DoubleVar(value=1.0)
        self.transparency_slider = ttk.Scale(self.transparency_frame,
                                           from_=0.1, to=1.0,
                                           orient=tk.HORIZONTAL,
                                           variable=self.transparency_var,
                                           command=self.update_transparency,
                                           length=100)
        self.transparency_slider.pack(side=tk.LEFT)

        # Configure style for label
        style.configure("Main.TLabel",
                       background='#f0f0f0',
                       font=('Segoe UI', 9))

        # Add hover tooltips
        self.create_tooltips()

        # Start monitoring
        self.running = True
        self.initial_scan()
        self.start_process_monitor()

        # Configure minimum window size to prevent columns from disappearing
        self.minsize(525, 400)  # Increased width for transparency controls

    def create_tooltips(self):
        """Create tooltips for buttons"""
        self.create_tooltip(self.end_button, "Terminate the selected process")
        self.create_tooltip(self.refresh_button, "Manually refresh the process list")
        self.create_tooltip(self.transparency_slider, "Adjust window transparency")

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, justify=tk.LEFT,
                           background="#ffffe0", relief="solid", borderwidth=1,
                           font=("Segoe UI", "8", "normal"))
            label.pack()

        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()

        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

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

    def get_process_icon(self, process_name, pid):
        """Get icon for a process"""
        try:
            # Check cache first
            if pid in self.icon_cache:
                return self.icon_cache[pid]

            # Try to get process path
            process = psutil.Process(pid)
            try:
                exe_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return self.get_default_icon(process_name)

            if not os.path.exists(exe_path):
                return self.get_default_icon(process_name)

            # Extract icon - use large icons for better quality
            large, small = win32gui.ExtractIconEx(exe_path, 0)
            if not large:
                return self.get_default_icon(process_name)

            icon_handle = large[0]  # Use large icon instead of small
            
            # Get system metrics for large icons
            ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
            ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
            hdc = hdc.CreateCompatibleDC()

            hdc.SelectObject(hbmp)
            hdc.DrawIcon((0, 0), icon_handle)

            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGBA', 
                (ico_x, ico_y),
                bmpstr, 
                'raw', 
                'BGRA', 
                0, 
                1
            )

            # Resize with high-quality resampling
            img = img.resize((20, 20), Image.Resampling.LANCZOS)

            # Clean up
            win32gui.DestroyIcon(icon_handle)
            if small:
                win32gui.DestroyIcon(small[0])
            hdc.DeleteDC()
            win32gui.ReleaseDC(0, hdc.GetHandleOutput())

            # Convert to PhotoImage and cache it
            photo = ImageTk.PhotoImage(img)
            self.icon_cache[pid] = photo
            return photo

        except Exception as e:
            return self.get_default_icon(process_name)

    def get_default_icon(self, process_name):
        """Create a default icon based on process type"""
        try:
            # Define paths
            system32 = os.path.join(os.environ['SystemRoot'], 'System32')
            shell32 = os.path.join(system32, 'shell32.dll')
            imageres = os.path.join(system32, 'imageres.dll')

            # Map process names to specific icons
            process_icons = {
                'taskmgr.exe': (imageres, 70),  # Task Manager icon
                'memcompression': (imageres, 109),  # Memory compression icon
                'searchhost.exe': (shell32, 23),  # Search icon
                'amdrssrv.exe': (shell32, 15),  # Service icon
                'dock_64.exe': (shell32, 44),  # Application icon
                'textinputhost.exe': (shell32, 16),  # Text input icon
                'explorer.exe': (shell32, 3),  # Explorer icon
                'svchost.exe': (imageres, 0),  # System process icon
                'services.exe': (imageres, 0),
                'lsass.exe': (imageres, 0),
            }

            # Get icon path and index for known processes
            if process_name.lower() in process_icons:
                ico_path, idx = process_icons[process_name.lower()]
            # Default icons for different types of processes
            elif process_name.lower().endswith('svc.exe') or process_name.lower().endswith('service.exe'):
                ico_path, idx = shell32, 57  # Service icon
            elif process_name.lower().endswith('.exe'):
                ico_path, idx = shell32, 2  # Generic application icon
            else:
                ico_path, idx = shell32, 1  # Generic file icon

            # Extract icon from system files
            large, small = win32gui.ExtractIconEx(ico_path, idx)
            if large:
                icon_handle = large[0]
                
                # Get system metrics for large icons
                ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
                ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
                hdc = hdc.CreateCompatibleDC()

                hdc.SelectObject(hbmp)
                hdc.DrawIcon((0, 0), icon_handle)

                bmpstr = hbmp.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGBA', 
                    (ico_x, ico_y),
                    bmpstr, 
                    'raw', 
                    'BGRA', 
                    0, 
                    1
                )

                # Resize with high-quality resampling
                img = img.resize((20, 20), Image.Resampling.LANCZOS)

                # Clean up
                win32gui.DestroyIcon(icon_handle)
                if small:
                    win32gui.DestroyIcon(small[0])
                hdc.DeleteDC()
                win32gui.ReleaseDC(0, hdc.GetHandleOutput())

                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                return photo

        except Exception as e:
            # Fallback to basic icon
            img = Image.new('RGBA', (20, 20), (200, 200, 200, 255))
            photo = ImageTk.PhotoImage(img)
            return photo

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
        for name, pid, memory in processes:
            try:
                icon = self.get_process_icon(name, pid)
                item_id = self.tree.insert('', 'end', text='')  # Create item without values first
                if icon:
                    self.tree.item(item_id, image=icon)  # Set icon separately
                self.tree.set(item_id, 'Name', name)  # Set each column value separately
                self.tree.set(item_id, 'PID', str(pid))
                self.tree.set(item_id, 'Memory', f"{memory:.1f}")
            except Exception as e:
                continue  # Skip any problematic entries

    def refresh_processes(self):
        """Manual refresh button handler"""
        self.single_scan()
        # Update current processes set
        self.current_processes = set(proc.pid for proc in psutil.process_iter())

    def end_process(self):
        selected_item = self.tree.selection()
        if selected_item:
            pid = int(self.tree.item(selected_item)['values'][1])  # PID is now the second column
            try:
                psutil.Process(pid).terminate()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                tk.messagebox.showerror("Error", "Access denied to terminate this process")

    def on_closing(self):
        """Clean up when closing the window"""
        self.running = False
        # Clear icon cache
        self.icon_cache.clear()
        self.destroy()

    def update_transparency(self, *args):
        """Update window transparency"""
        alpha = self.transparency_var.get()
        self.attributes('-alpha', alpha)

if __name__ == "__main__":
    app = ProcessWidget()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 