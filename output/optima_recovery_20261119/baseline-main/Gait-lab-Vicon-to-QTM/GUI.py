from pyside6_compat import tk, ttk, filedialog, messagebox, scrolledtext
import os
import subprocess
import threading
import ctypes
from gapi import getProjDirectory
# Global variable for conda environment name
CONDA_ENV_NAME = "python-example"  # Change this to your actual conda environment name

class GaitAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gait Analysis Tool")
        
        # Enable DPI awareness for Windows
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # Make window responsive
        self.root.minsize(700, 550)
        
        # Configure window to be scalable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        # Modern color scheme
        self.bg_color = "#f5f5f5"
        self.primary_color = "#0078d4"
        self.secondary_color = "#00b294"
        self.text_color = "#323130"
        
        self.root.configure(bg=self.bg_color)
        
        # Create main content frame with padding - centered
        main_frame = tk.Frame(root, bg=self.bg_color)
        main_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Title label with modern styling
        title_label = tk.Label(main_frame, text="Gait Analysis Tool", 
                              font=('Segoe UI', 24, 'bold'),
                              fg=self.text_color, bg=self.bg_color)
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame, text="Select an analysis type to begin",
                                 font=('Segoe UI', 10),
                                 fg="#605e5c", bg=self.bg_color)
        subtitle_label.pack(pady=(0, 30))
        
        # Buttons frame for better layout
        buttons_frame = tk.Frame(main_frame, bg=self.bg_color)
        buttons_frame.pack(pady=20)
        
        # Modern styled buttons using ttk
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom button styles
        style.configure('Static.TButton',
                       font=('Segoe UI', 11),
                       padding=15,
                       relief='flat')
        
        style.configure('Dynamic.TButton',
                       font=('Segoe UI', 11),
                       padding=15,
                       relief='flat')
        
        # Static analysis button
        self.static_btn = tk.Button(buttons_frame, text="🔬 Perform Static Analysis",
                              command=self.perform_static_analysis,
                              font=('Segoe UI', 12, 'bold'),
                              bg='#0078d4', fg='white',
                              activebackground='#106ebe',
                              activeforeground='white',
                              relief='flat',
                              cursor='hand2',
                              width=30,
                              padx=20, pady=12)
        self.static_btn.pack(pady=8)
        
        # Dynamic analysis button
        self.dynamic_btn = tk.Button(buttons_frame, text="⚡ Perform Dynamic Analysis",
                               command=self.perform_dynamic_analysis,
                               font=('Segoe UI', 12, 'bold'),
                               bg='#00b294', fg='white',
                               activebackground='#009b7d',
                               activeforeground='white',
                               relief='flat',
                               cursor='hand2',
                               width=30,
                               padx=20, pady=12)
        self.dynamic_btn.pack(pady=8)
        self.auto_btn = tk.Button(main_frame, text="Run Auto Event Labeling",
                              command=self.perform_auto_labeling,
                              font=('Segoe UI', 12, 'bold'),
                               bg="#5c00b2", fg='white',
                               activebackground="#003e9b",
                               activeforeground='white',
                               relief='flat',
                               cursor='hand2',
                               width=30,
                               padx=20, pady=12)
        self.auto_btn.pack(pady=8)
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill='x', pady=20)
        
        # Logging section
        logging_frame = tk.Frame(main_frame, bg=self.bg_color)
        logging_frame.pack(pady=10)
        
        # Logging checkbox with modern style
        self.logging_var = tk.BooleanVar(value=False)
        style.configure('Modern.TCheckbutton',
                       font=('Segoe UI', 10),
                       background=self.bg_color)
        
        logging_checkbox = ttk.Checkbutton(logging_frame, text="Enable Detailed Logging",
                                          variable=self.logging_var,
                                          command=self.toggle_logging,
                                          style='Modern.TCheckbutton')
        logging_checkbox.pack(anchor='w')
        
        # Log output text area (initially hidden)
        self.log_frame = tk.Frame(main_frame, bg=self.bg_color)
        
        log_header = tk.Frame(self.log_frame, bg=self.bg_color)
        log_header.pack(fill='x', pady=(10, 5))
        
        log_label = tk.Label(log_header, text="📋 Output Log:", 
                            font=('Segoe UI', 11, 'bold'),
                            fg=self.text_color, bg=self.bg_color)
        log_label.pack(side='left')
        
        # Clear log button in header
        clear_btn = tk.Button(log_header, text="Clear",
                             command=self.clear_log,
                             font=('Segoe UI', 9),
                             bg='#e1dfdd', fg=self.text_color,
                             relief='flat',
                             cursor='hand2',
                             padx=15, pady=5)
        clear_btn.pack(side='right')
        
        # Log text area with modern styling
        log_text_frame = tk.Frame(self.log_frame, bg='white', relief='solid', bd=1)
        log_text_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_text_frame, 
                                                  height=12,
                                                  font=('Consolas', 9),
                                                  bg='#1e1e1e', fg='#d4d4d4',
                                                  insertbackground='white',
                                                  relief='flat',
                                                  padx=10, pady=10)
        self.log_text.pack(fill='both', expand=True)
        
        # Store button references for enable/disable
        self.buttons = [self.static_btn, self.dynamic_btn,self.auto_btn]
        
    def toggle_logging(self):
        """Toggle visibility of logging area"""
        if self.logging_var.get():
            self.log_frame.pack(pady=15, fill='both', expand=True)
        else:
            self.log_frame.pack_forget()
    
    def clear_log(self):
        """Clear the log text area"""
        self.log_text.delete(1.0, tk.END)
    
    def log_message(self, message):
        """Add message to log if logging is enabled"""
        if self.logging_var.get():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)  # Auto-scroll to bottom

        
    def select_qtm_file(self):
        """Open file dialog to select .qtm file and return processed path info"""
        # Get current directory
        
        try:
            current_dir=getProjDirectory()
        except Exception as e:
            current_dir = os.getcwd()
        
        # Open file dialog with .qtm filter
        file_path = filedialog.askopenfilename(
            title="Select QTM file",
            initialdir=current_dir,
            filetypes=[("QTM files", "*.qtm"), ("All files", "*.*")]
        )
        
        if file_path:
            # Split path into directory and filename
            dir_path = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # Create session.xml path
            session_xml_path = os.path.join(dir_path, "session.xml")
            
            return (session_xml_path, filename)
        
        return None
    def perform_auto_labeling(self):
        """Handle auto event labeling button click (allows multiple files)."""
        results = self.select_qtm_file()
        if results:
            self.disable_buttons()
            thread = threading.Thread(
                target=self.run_auto_labeling_thread,
                args=(results,)
            )
            thread.daemon = True
            thread.start()
    def run_auto_labeling_thread(self, file_list):
        """Background worker that runs event labeling for each selected file."""
        try:
            session_xml_path, filename = file_list
            qtm_path = os.path.join(os.path.dirname(session_xml_path), filename)
            self.log_message(f"Auto-labeling {qtm_path}...")
            # Use existing helper with relative path up one directory
            try:
                self.run_script_in_conda("auto_event_trigger.py", session_xml_path, filename)
            except Exception as e:
                self.log_message(f"Error launching auto_event_trigger via conda: {e}")
        finally:
            self.root.after(0, self.enable_buttons)

    def run_script_in_conda(self, script_name, session_xml_path, filename):
        """Run Python script in conda environment"""
        try:
            # Create command to run script in conda environment
            cmd = [
                "conda", "run", "-n", CONDA_ENV_NAME,
                "python", Path(__file__).parent / script_name,"-s",
                session_xml_path, "-f", filename,"-t","BF"
            ]
            
            self.log_message(f"Running command: {' '.join(map(str, cmd))}")
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            # Log stdout if available
            if result.stdout:
                self.log_message("STDOUT:")
                self.log_message(result.stdout)
            
            # Log stderr if available
            if result.stderr:
                self.log_message("STDERR:")
                self.log_message(result.stderr)
            
            if result.returncode == 0:
                self.log_message(f"Script {script_name} completed successfully!")
                messagebox.showinfo("Success", 
                                   f"Script {script_name} completed successfully!\n"
                                   f"Output: {result.stdout}")
            else:
                self.log_message(f"Script {script_name} failed with return code {result.returncode}")
                messagebox.showerror("Error", 
                                   f"Script {script_name} failed!\n"
                                   f"Error: {result.stderr}")
                
        except Exception as e:
            error_msg = f"Failed to run script: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def perform_static_analysis(self):
        """Handle static analysis button click"""
        result = self.select_qtm_file()
        if result:
            session_xml_path, filename = result
            
            # Disable button to prevent multiple clicks
            self.disable_buttons()
            
            # Run script in separate thread to prevent GUI freezing
            thread = threading.Thread(
                target=self.run_static_analysis_thread,
                args=(session_xml_path, filename)
            )
            thread.daemon = True
            thread.start()
    
    def run_static_analysis_thread(self, session_xml_path, filename):
        """Run static analysis in separate thread"""
        try:
            self.run_script_in_conda("Py3_StaticMain.py", session_xml_path, filename)
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons)
    
    def perform_dynamic_analysis(self):
        """Handle dynamic analysis button click"""
        result = self.select_qtm_file()
        if result:
            session_xml_path, filename = result
            
            # Disable button to prevent multiple clicks
            self.disable_buttons()
            
            # Run script in separate thread to prevent GUI freezing
            thread = threading.Thread(
                target=self.run_dynamic_analysis_thread,
                args=(session_xml_path, filename)
            )
            thread.daemon = True
            thread.start()
    
    def run_dynamic_analysis_thread(self, session_xml_path, filename):
        """Run dynamic analysis in separate thread"""
        try:
            self.run_script_in_conda("Py3_DynamicMain.py", session_xml_path, filename)
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons)
    
    def disable_buttons(self):
        """Disable all buttons during script execution"""
        for button in self.buttons:
            button.config(state='disabled')
    
    def enable_buttons(self):
        """Enable all buttons after script execution"""
        for button in self.buttons:
            button.config(state='normal')

def main():
    root = tk.Tk()
    app = GaitAnalysisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()