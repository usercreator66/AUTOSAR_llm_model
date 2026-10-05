#include <stdint.h>
python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

class CodeGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Generator")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Define supported languages
        self.languages = {
            "Python": ".py",
            "C": ".c",
            "C++": ".cpp",
            "Java": ".java",
            "JavaScript": ".js",
            "HTML": ".html",
            "CSS": ".css",
            "SQL": ".sql",
            "PHP": ".php",
            "Go": ".go",
            "Rust": ".rs",
            "Swift": ".swift",
            "Kotlin": ".kt"
        }

        # Create UI
        self.create_widgets()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Prompt Label and Entry
        ttk.Label(main_frame, text="Prompt:").grid(row=0, column=0, sticky="w", pady=5)
        self.prompt_entry = ttk.Entry(main_frame, width=60)
        self.prompt_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)

        # Language Dropdown
        ttk.Label(main_frame, text="Language:").grid(row=1, column=0, sticky="w", pady=5)
        self.language_var = tk.StringVar(value="Python")
        self.language_combo = ttk.Combobox(main_frame, textvariable=self.language_var, values=list(self.languages.keys()), state="readonly", width=20)
        self.language_combo.grid(row=1, column=1, sticky="w", pady=5)

        # File Extension Label and Entry
        ttk.Label(main_frame, text="File Extension:").grid(row=1, column=2, sticky="w", pady=5)
        self.extension_entry = ttk.Entry(main_frame, width=20)
        self.extension_entry.insert(0, self.languages[self.language_var.get()])
        self.extension_entry.grid(row=1, column=3, sticky="w", pady=5)

        # Output Path Label and Entry
        ttk.Label(main_frame, text="Output Path:").grid(row=2, column=0, sticky="w", pady=5)
        self.output_path_entry = ttk.Entry(main_frame, width=60)
        self.output_path_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)

        # Browse Button
        ttk.Button(main_frame, text="Browse...", command=self.browse_output).grid(row=2, column=3, sticky="w", pady=5)

        # Generate Button
        self.generate_btn = ttk.Button(main_frame, text="Generate Code", command=self.generate_code)
        self.generate_btn.grid(row=3, column=0, columnspan=4, pady=10)

        # Preview Frame
        preview_frame = ttk.LabelFrame(main_frame, text="Generated Code Preview", padding="5")
        preview_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=10)

        self.preview_text = tk.Text(preview_frame, height=10, width=80)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Save Button
        self.save_btn = ttk.Button(preview_frame, text="Save to File", command=self.save_code)
        self.save_btn.pack(side=tk.right, padx=5)

        # Clear Button
        self.clear_btn = ttk.Button(preview_frame, text="Clear", command=self.clear_preview)
        self.clear_btn.pack(side=tk.right, padx=5)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path_entry.delete(0, tk.END)
            self.output_path_entry.insert(0, path)

    def generate_code(self):
        prompt = self.prompt_entry.get().strip()
        lang = self.language_var.get()
        ext = self.extension_entry.get().strip()
        output_path = self.output_path_entry.get().strip()

        if not prompt:
            messagebox.showwarning("Warning", "Please enter a prompt.")
            return

        if not ext:
            messagebox.showwarning("Warning", "Please specify a file extension.")
            return

        if not output_path:
            messagebox.showwarning("Warning", "Please specify an output path.")
            return

        # Generate code based on language
        code = self.generate_code_template(lang, prompt)

        # Update preview
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, code)

        # Save to file
        self.save_code()

    def generate_code_template(self, lang, prompt):
        templates = {
            "Python": f"""# Code generated for: {prompt}
# Language: Python
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

def main():
    # TODO: Implement logic for {prompt}
    pass

if __name__ == "__main__":
    main()""",
            "C": f"""/* Code generated for: {prompt} */
/* Language: C */
/* Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */

#include <stdio.h>

int main() {{
    // TODO: Implement logic for {prompt}
    return 0;
}}}""",
            "C++": f"""// Code generated for: {prompt}
// Language: C++
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#include <iostream>

int main() {{
    // TODO: Implement logic for {prompt}
    return 0;
}}}""",
            "Java": f"""// Code generated for: {prompt}
// Language: Java
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

public class Main {{
    public static void main(String[] args) {{
        // TODO: Implement logic for {prompt}
    }}
}}""",
            "JavaScript": f"""// Code generated for: {prompt}
// Language: JavaScript
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

function main() {{
    // TODO: Implement logic for {prompt}
}}""",
            "HTML": f"""<!-- Code generated for: {prompt} -->
<!-- Language: HTML -->
<!-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->

<!DOCTYPE html>
<html>
<head>
    <title>{prompt}</title>
</head>
<body>
    <!-- TODO: Implement content for {prompt} -->
</body>
</html>""",
            "CSS": f"""/* Code generated for: {prompt} */
/* Language: CSS */
/* Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */

body {{
    /* TODO: Implement styles for {prompt} */
}}""",
            "SQL": f"""-- Code generated for: {prompt}
-- Language: SQL
-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-- TODO: Implement query for {prompt}
SELECT * FROM table_name;""",
            "PHP": f"""<?php
// Code generated for: {prompt}
// Language: PHP
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

// TODO: Implement logic for {prompt}
?>""",
            "Go": f"""// Code generated for: {prompt}
// Language: Go
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

package main

import "fmt"

func main() {{
    // TODO: Implement logic for {prompt}
    fmt.Println("Hello, World!")
}}}""",
            "Rust": f"""// Code generated for: {prompt}
// Language: Rust
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

fn main() {{
    // TODO: Implement logic for {prompt}
    println!("Hello, World!");
}}}""",
            "Swift": f"""// Code generated for: {prompt}
// Language: Swift
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

import UIKit

class ViewController: UIViewController {{
    override func viewDidLoad() {{
        super.viewDidLoad()
        // TODO: Implement logic for {prompt}
    }}
}}""",
            "Kotlin": f"""// Code generated for: {prompt}
// Language: Kotlin
// Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

fun main() {{
    // TODO: Implement logic for {prompt}
    println("Hello, World!")
}}}"""
        }

        return templates.get(lang, f"""# Code generated for: {prompt}
# Language: {lang}
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# TODO: Implement logic for {prompt}
pass""")

    def save_code(self):
        code = self.preview_text.get(1.0, tk.END)
        ext = self.extension_entry.get().strip()
        output_path = self.output_path_entry.get().strip()

        if not code or not output_path:
            messagebox.showwarning("Warning", "Please enter code and specify an output path.")
            return

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code)
            messagebox.showinfo("Success", f"Code saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def clear_preview(self):
        self.preview_text.delete(1.0, tk.END)

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = CodeGeneratorApp(root)
    root.mainloop()
