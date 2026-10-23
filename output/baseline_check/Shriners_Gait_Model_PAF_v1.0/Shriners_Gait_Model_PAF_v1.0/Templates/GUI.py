from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox,scrolledtext
import os
import subprocess
import threading

# Global variable for conda environment name
CONDA_ENV_NAME = "python-example"  # Change this to your actual conda environment name

class GaitAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gait Analysis Tool")
        self.root.geometry("600x500")
        
        # Create main frame
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(expand=True, fill='both')
        
        # Title label
        title_label = tk.Label(main_frame, text="Gait Analysis Tool", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Static analysis button
        static_btn = tk.Button(main_frame, text="Perform Static Analysis",
                              command=self.perform_static_analysis,
                              width=25, height=2,
                              bg='lightblue')
        static_btn.pack(pady=10)
        
        # Dynamic analysis button
        dynamic_btn = tk.Button(main_frame, text="Perform Dynamic Analysis",
                               command=self.perform_dynamic_analysis,
                               width=25, height=2,
                               bg='lightgreen')
        dynamic_btn.pack(pady=10)
        
        # Logging checkbox
        self.logging_var = tk.BooleanVar(value=False)
        logging_checkbox = tk.Checkbutton(main_frame, text="Enable Logging",
                                         variable=self.logging_var,
                                         command=self.toggle_logging)
        logging_checkbox.pack(pady=10)
        
        # Log output text area (initially hidden)
        self.log_frame = tk.Frame(main_frame)
        log_label = tk.Label(self.log_frame, text="Output Log:", font=('Arial', 10, 'bold'))
        log_label.pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=15, width=70)
        self.log_text.pack(fill='both', expand=True)
        
        # Clear log button
        clear_btn = tk.Button(self.log_frame, text="Clear Log",
                             command=self.clear_log,
                             width=15, height=1)
        clear_btn.pack(pady=5)
        
    def toggle_logging(self):
        """Toggle visibility of logging area"""
        if self.logging_var.get():
            self.log_frame.pack(pady=10, fill='both', expand=True)
            self.root.geometry("600x700")  # Expand window
        else:
            self.log_frame.pack_forget()
            self.root.geometry("600x500")  # Return to original size
    
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
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(state='disabled')
    
    def enable_buttons(self):
        """Enable all buttons after script execution"""
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(state='normal')

def main():
    root = tk.Tk()
    app = GaitAnalysisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()