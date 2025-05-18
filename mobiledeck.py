from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_from_directory
from pynput.keyboard import Controller, Key
import json
import os
import base64
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import importlib.util
import sys
from datetime import datetime
import threading
import webbrowser
import socket
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
keyboard = Controller()
button_states = {}

def get_script_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def load_config():
    script_dir = get_script_directory()
    config_path = os.path.join(script_dir, 'config.py')
    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location("config", config_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        if not hasattr(config, 'profiles'):
            config.profiles = [
                {
                    "name": "Default",
                    "groups": [
                        {
                            "name": "Main",
                            "buttons": getattr(config, 'buttons', [])
                        }
                    ]
                }
            ]
        if not hasattr(config, 'default_preferences'):
            config.default_preferences = {
                "theme": "dark",
                "buttons_per_row": 3, 
                "button_height": 100,
                "button_width": 120
            }
        return config
    else:
        class DefaultConfig:
            def __init__(self):
                self.profiles = [
                    {
                        "name": "Default",
                        "groups": [
                            {
                                "name": "Main",
                                "buttons": []
                            }
                        ]
                    }
                ]
                self.default_preferences = {
                    "theme": "dark",
                    "buttons_per_row": 3,
                    "button_height": 100,
                    "button_width": 120
                }
                self.active_profile = "Default"
                self.active_group = "Main"
        return DefaultConfig()

def save_config(config_data):
    script_dir = get_script_directory()
    config_path = os.path.join(script_dir, 'config.py')
    with open(config_path, 'w') as f:
        f.write("profiles = [\n")
        for profile in config_data["profiles"]:
            f.write("    {\n")
            f.write(f"        \"name\": \"{profile['name']}\",\n")
            f.write("        \"groups\": [\n")
            for group in profile["groups"]:
                f.write("            {\n")
                f.write(f"                \"name\": \"{group['name']}\",\n")
                f.write("                \"buttons\": [\n")
                for button in group["buttons"]:
                    f.write("                    {\n")
                    f.write(f"                        \"text\": \"{button['text']}\",\n")
                    f.write(f"                        \"color\": \"{button['color']}\",\n")
                    f.write(f"                        \"text_color\": \"{button['text_color']}\",\n")
                    if button['image']:
                        f.write(f"                        \"image\": \"{button['image']}\",\n")
                    else:
                        f.write("                        \"image\": None,\n")
                    f.write("                        \"hotkey\": [")
                    for i, key in enumerate(button["hotkey"]):
                        if i > 0:
                            f.write(", ")
                        f.write(f"\"{key}\"")
                    f.write("],\n")
                    if "sequence" in button and button["sequence"]:
                        f.write("                        \"sequence\": [\n")
                        for seq in button["sequence"]:
                            f.write("                            [")
                            for i, key in enumerate(seq):
                                if i > 0:
                                    f.write(", ")
                                f.write(f"\"{key}\"")
                            f.write("],\n")
                        f.write("                        ],\n")
                    f.write(f"                        \"is_toggle\": {str(button['is_toggle'])}\n")
                    f.write("                    },\n")
                f.write("                ]\n")
                f.write("            },\n")
            f.write("        ]\n")
            f.write("    },\n")
        f.write("]\n\n")
        f.write(f"active_profile = \"{config_data.get('active_profile', 'Default')}\"\n")
        f.write(f"active_group = \"{config_data.get('active_group', 'Main')}\"\n\n")
        f.write("default_preferences = {\n")
        for key, value in config_data["default_preferences"].items():
            if isinstance(value, str):
                f.write(f"    \"{key}\": \"{value}\",\n")
            else:
                f.write(f"    \"{key}\": {value},\n")
        f.write("}\n")

config = load_config()

def get_active_buttons():
    active_profile = getattr(config, 'active_profile', 'Default')
    active_group = getattr(config, 'active_group', 'Main')
    for profile in config.profiles:
        if profile['name'] == active_profile:
            for group in profile['groups']:
                if group['name'] == active_group:
                    return group['buttons']
    return []

class ButtonManager:
    def __init__(self, root=None):
        self.config_data = {
            "profiles": config.profiles,
            "default_preferences": config.default_preferences,
            "active_profile": getattr(config, 'active_profile', 'Default'),
            "active_group": getattr(config, 'active_group', 'Main')
        }
        if root is None:
            self.root = tk.Tk()
            self.root.title("MobileDeck Button Manager")
            self.root.geometry("1000x700")
            self.root.minsize(800, 600)
            self.setup_ui()
        else:
            self.root = root
    
    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.available_keys = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'ctrl', 'alt', 'shift', 'space', 'tab', 'enter', 'backspace', 'delete',
            'up', 'down', 'left', 'right', 'escape', 'home', 'end', 'page_up', 'page_down',
            'insert', 'print_screen', 'caps_lock', 'num_lock', 'scroll_lock', 'pause'
        ]
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)
        profiles_frame = ttk.LabelFrame(left_panel, text="Profiles")
        profiles_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        profiles_frame.columnconfigure(0, weight=1)
        self.profile_listbox = tk.Listbox(profiles_frame, height=5, exportselection=0)
        self.profile_listbox.grid(row=0, column=0, sticky="ew", padx=5, pady=5, columnspan=3)
        self.profile_listbox.bind('<<ListboxSelect>>', self.on_profile_select)
        add_profile_btn = ttk.Button(profiles_frame, text="+", width=3, command=self.add_profile)
        add_profile_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        rename_profile_btn = ttk.Button(profiles_frame, text="✏️", width=3, command=self.rename_profile)
        rename_profile_btn.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        delete_profile_btn = ttk.Button(profiles_frame, text="🗑️", width=3, command=self.delete_profile)
        delete_profile_btn.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        groups_frame = ttk.LabelFrame(left_panel, text="Groups")
        groups_frame.grid(row=1, column=0, sticky="nsew")
        groups_frame.columnconfigure(0, weight=1)
        groups_frame.rowconfigure(0, weight=1)
        self.group_listbox = tk.Listbox(groups_frame, exportselection=0)
        self.group_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5, columnspan=3)
        self.group_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        add_group_btn = ttk.Button(groups_frame, text="+", width=3, command=self.add_group)
        add_group_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        rename_group_btn = ttk.Button(groups_frame, text="✏️", width=3, command=self.rename_group)
        rename_group_btn.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        delete_group_btn = ttk.Button(groups_frame, text="🗑️", width=3, command=self.delete_group)
        delete_group_btn.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=0)
        buttons_frame = ttk.LabelFrame(right_panel, text="Buttons")
        buttons_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.rowconfigure(0, weight=1)
        self.buttons_listbox = tk.Listbox(buttons_frame, exportselection=0)
        self.buttons_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5, columnspan=3)
        self.buttons_listbox.bind('<<ListboxSelect>>', self.on_button_select)
        add_button_btn = ttk.Button(buttons_frame, text="+", width=3, command=self.add_button)
        add_button_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        duplicate_button_btn = ttk.Button(buttons_frame, text="📋", width=3, command=self.duplicate_button)
        duplicate_button_btn.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        delete_button_btn = ttk.Button(buttons_frame, text="🗑️", width=3, command=self.delete_button)
        delete_button_btn.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.editor_frame = ttk.LabelFrame(right_panel, text="Button Editor")
        self.editor_frame.grid(row=1, column=0, sticky="ew")
        self.editor_frame.columnconfigure(1, weight=1)
        ttk.Label(self.editor_frame, text="Button Text:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.button_text = ttk.Entry(self.editor_frame)
        self.button_text.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(self.editor_frame, text="Background Color:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        color_frame = ttk.Frame(self.editor_frame)
        color_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        color_frame.columnconfigure(0, weight=1)
        self.bg_color = ttk.Entry(color_frame)
        self.bg_color.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.bg_color_btn = ttk.Button(color_frame, text="Pick Color", command=lambda: self.pick_color(self.bg_color))
        self.bg_color_btn.grid(row=0, column=1)
        ttk.Label(self.editor_frame, text="Text Color:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        text_color_frame = ttk.Frame(self.editor_frame)
        text_color_frame.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        text_color_frame.columnconfigure(0, weight=1)
        self.text_color = ttk.Entry(text_color_frame)
        self.text_color.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.text_color_btn = ttk.Button(text_color_frame, text="Pick Color", command=lambda: self.pick_color(self.text_color))
        self.text_color_btn.grid(row=0, column=1)
        ttk.Label(self.editor_frame, text="Image URL:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.image_url = ttk.Entry(self.editor_frame)
        self.image_url.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        self.is_toggle = tk.BooleanVar()
        toggle_check = ttk.Checkbutton(self.editor_frame, text="Toggle Button", variable=self.is_toggle)
        toggle_check.grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        seq_frame = ttk.LabelFrame(self.editor_frame, text="Key Combinations")
        seq_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        seq_frame.columnconfigure(0, weight=1)
        self.seq_listbox = tk.Listbox(seq_frame, height=4)
        self.seq_listbox.grid(row=0, column=0, sticky="ew", padx=5, pady=5, columnspan=3)
        add_seq_btn = ttk.Button(seq_frame, text="+", width=3, command=self.add_sequence)
        add_seq_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        edit_seq_btn = ttk.Button(seq_frame, text="✏️", width=3, command=self.edit_sequence)
        edit_seq_btn.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        delete_seq_btn = ttk.Button(seq_frame, text="🗑️", width=3, command=self.delete_sequence)
        delete_seq_btn.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        buttons_frame = ttk.Frame(self.editor_frame)
        buttons_frame.grid(row=6, column=0, columnspan=2, sticky="e", padx=5, pady=10)
        save_btn = ttk.Button(buttons_frame, text="Save Button", command=self.save_button)
        save_btn.grid(row=0, column=0, padx=(0, 5))
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self.cancel_edit)
        cancel_btn.grid(row=0, column=1)
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        save_all_btn = ttk.Button(bottom_frame, text="Save All Changes", command=self.save_all)
        save_all_btn.grid(row=0, column=0, padx=5)
        self.refresh_profiles()
        self.current_button_index = None
        self.sequence_data = []
        self.disable_editor()
    
    def refresh_profiles(self):
        self.profile_listbox.delete(0, tk.END)
        active_profile = self.config_data.get("active_profile", "Default")
        active_index = 0
        for i, profile in enumerate(self.config_data["profiles"]):
            self.profile_listbox.insert(tk.END, profile["name"])
            if profile["name"] == active_profile:
                active_index = i
        if self.profile_listbox.size() > 0:
            self.profile_listbox.selection_set(active_index)
            self.profile_listbox.see(active_index)
            self.on_profile_select()
    
    def refresh_groups(self):
        self.group_listbox.delete(0, tk.END)
        selected_profile = self.get_selected_profile()
        active_group = self.config_data.get("active_group", "Main")
        active_index = 0
        if selected_profile:
            for i, group in enumerate(selected_profile["groups"]):
                self.group_listbox.insert(tk.END, group["name"])
                if group["name"] == active_group:
                    active_index = i
            if self.group_listbox.size() > 0:
                self.group_listbox.selection_set(active_index)
                self.group_listbox.see(active_index)
                self.on_group_select()
    
    def refresh_buttons(self):
        self.buttons_listbox.delete(0, tk.END)
        selected_group = self.get_selected_group()
        if selected_group:
            for button in selected_group["buttons"]:
                self.buttons_listbox.insert(tk.END, button["text"])
    
    def refresh_sequences(self):
        self.seq_listbox.delete(0, tk.END)
        for i, seq in enumerate(self.sequence_data):
            prefix = "➊ " if i == 0 else f"➋ Step {i}: "
            self.seq_listbox.insert(tk.END, f"{prefix}{' + '.join(seq)}")
    
    def get_selected_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index < len(self.config_data["profiles"]):
            return self.config_data["profiles"][index]
        return None
    
    def get_selected_group(self):
        profile = self.get_selected_profile()
        if not profile:
            return None
        selection = self.group_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index < len(profile["groups"]):
            return profile["groups"][index]
        return None
    
    def get_selected_button(self):
        group = self.get_selected_group()
        if not group:
            return None
        selection = self.buttons_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index < len(group["buttons"]):
            self.current_button_index = index
            return group["buttons"][index]
        return None
    
    def on_profile_select(self, event=None):
        self.refresh_groups()
        self.disable_editor()
    
    def on_group_select(self, event=None):
        self.refresh_buttons()
        self.disable_editor()
    
    def on_button_select(self, event=None):
        button = self.get_selected_button()
        if button:
            self.enable_editor()
            self.button_text.delete(0, tk.END)
            self.button_text.insert(0, button["text"])
            self.bg_color.delete(0, tk.END)
            self.bg_color.insert(0, button["color"])
            self.text_color.delete(0, tk.END)
            self.text_color.insert(0, button["text_color"])
            self.image_url.delete(0, tk.END)
            if button["image"]:
                self.image_url.insert(0, button["image"])
            self.is_toggle.set(button.get("is_toggle", False))
            self.sequence_data = []
            if button["hotkey"]:
                self.sequence_data.append(button["hotkey"])
            if "sequence" in button and button["sequence"]:
                self.sequence_data.extend(button["sequence"])
            self.refresh_sequences()
    
    def enable_editor(self):
        for child in self.editor_frame.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subchild, (ttk.Entry, ttk.Button, tk.Listbox)):
                    subchild.configure(state="normal")
            if isinstance(child, (ttk.Entry, ttk.Button, ttk.Checkbutton, tk.Listbox)):
                child.configure(state="normal")
    
    def disable_editor(self):
        self.current_button_index = None
        self.sequence_data = []
        self.button_text.delete(0, tk.END)
        self.bg_color.delete(0, tk.END)
        self.text_color.delete(0, tk.END)
        self.image_url.delete(0, tk.END)
        self.is_toggle.set(False)
        self.seq_listbox.delete(0, tk.END)
        for child in self.editor_frame.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subchild, (ttk.Entry, ttk.Button, tk.Listbox)):
                    subchild.configure(state="disabled")
            if isinstance(child, (ttk.Entry, ttk.Button, ttk.Checkbutton, tk.Listbox)):
                child.configure(state="disabled")
    
    def pick_color(self, entry_widget):
        current_color = entry_widget.get() or "#000000"
        color = colorchooser.askcolor(color=current_color)[1]
        if color:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, color)
    
    def add_sequence(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Key Combination")
        dialog.geometry("400x300")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Add keys for this combination:").pack(pady=(10, 5))
        keys_frame = ttk.Frame(dialog)
        keys_frame.pack(fill="both", expand=True, padx=10, pady=5)
        key_vars = []
        key_dropdowns = []
        def add_key_dropdown():
            key_var = tk.StringVar()
            key_vars.append(key_var)
            key_row = ttk.Frame(keys_frame)
            key_row.pack(fill="x", pady=2)
            key_dropdown = ttk.Combobox(key_row, textvariable=key_var, values=self.available_keys, width=15)
            key_dropdown.pack(side="left", padx=(0, 5))
            key_dropdowns.append(key_dropdown)
            delete_btn = ttk.Button(key_row, text="🗑️", width=3, 
                                   command=lambda r=key_row, v=key_var, d=key_dropdown: remove_key(r, v, d))
            delete_btn.pack(side="left")
            return key_dropdown
        def remove_key(row, var, dropdown):
            if len(key_vars) > 1:
                row.destroy()
                key_vars.remove(var)
                key_dropdowns.remove(dropdown)
        first_dropdown = add_key_dropdown()
        first_dropdown.focus_set()
        add_key_btn = ttk.Button(dialog, text="+ Add Key", command=add_key_dropdown)
        add_key_btn.pack(pady=5)
        def on_ok():
            selected_keys = [var.get() for var in key_vars if var.get()]
            if selected_keys:
                self.sequence_data.append(selected_keys)
                self.refresh_sequences()
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side="right", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side="right", padx=5)
    
    def edit_sequence(self):
        selection = self.seq_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self.sequence_data):
            return
        existing_sequence = self.sequence_data[index]
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Key Combination")
        dialog.geometry("400x300")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Edit keys for this combination:").pack(pady=(10, 5))
        keys_frame = ttk.Frame(dialog)
        keys_frame.pack(fill="both", expand=True, padx=10, pady=5)
        key_vars = []
        key_dropdowns = []
        key_rows = []
        def add_key_dropdown(initial_value=None):
            key_var = tk.StringVar(value=initial_value if initial_value else "")
            key_vars.append(key_var)
            key_row = ttk.Frame(keys_frame)
            key_row.pack(fill="x", pady=2)
            key_rows.append(key_row)
            key_dropdown = ttk.Combobox(key_row, textvariable=key_var, values=self.available_keys, width=15)
            key_dropdown.pack(side="left", padx=(0, 5))
            key_dropdowns.append(key_dropdown)
            delete_btn = ttk.Button(key_row, text="🗑️", width=3, 
                                   command=lambda r=key_row, v=key_var, d=key_dropdown: remove_key(r, v, d))
            delete_btn.pack(side="left")
            return key_dropdown
        def remove_key(row, var, dropdown):
            if len(key_vars) > 1:
                idx = key_rows.index(row)
                row.destroy()
                key_rows.pop(idx)
                key_vars.pop(idx)
                key_dropdowns.pop(idx)
        for key in existing_sequence:
            add_key_dropdown(key)
        if not key_vars:
            add_key_dropdown()
        add_key_btn = ttk.Button(dialog, text="+ Add Key", command=lambda: add_key_dropdown())
        add_key_btn.pack(pady=5)
        def on_ok():
            selected_keys = [var.get() for var in key_vars if var.get()]
            if selected_keys:
                self.sequence_data[index] = selected_keys
                self.refresh_sequences()
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side="right", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side="right", padx=5)
    
    def delete_sequence(self):
        selection = self.seq_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index < len(self.sequence_data):
            del self.sequence_data[index]
            self.refresh_sequences()
    
    def add_profile(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Profile")
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Profile Name:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(fill="x", padx=20, pady=5)
        name_entry.focus_set()
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Profile name cannot be empty")
                return
            for profile in self.config_data["profiles"]:
                if profile["name"] == name:
                    messagebox.showerror("Error", f"Profile '{name}' already exists")
                    return
            self.config_data["profiles"].append({
                "name": name,
                "groups": [
                    {
                        "name": "Main",
                        "buttons": []
                    }
                ]
            })
            self.refresh_profiles()
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
    
    def rename_profile(self):
        profile = self.get_selected_profile()
        if not profile:
            return
        old_name = profile["name"]
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Profile")
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="New Profile Name:").pack(pady=(10, 0))
        name_var = tk.StringVar(value=old_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(fill="x", padx=20, pady=5)
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Profile name cannot be empty")
                return
            if name != old_name:
                for p in self.config_data["profiles"]:
                    if p["name"] == name and p != profile:
                        messagebox.showerror("Error", f"Profile '{name}' already exists")
                        return
                profile["name"] = name
                if self.config_data["active_profile"] == old_name:
                    self.config_data["active_profile"] = name
                self.refresh_profiles()
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
    
    def delete_profile(self):
        profile = self.get_selected_profile()
        if not profile:
            return
        if len(self.config_data["profiles"]) <= 1:
            messagebox.showerror("Error", "Cannot delete the last profile")
            return
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{profile['name']}'?"):
            selection = self.profile_listbox.curselection()[0]
            del self.config_data["profiles"][selection]
            if self.config_data["active_profile"] == profile["name"]:
                self.config_data["active_profile"] = self.config_data["profiles"][0]["name"]
            self.refresh_profiles()
    
    def add_group(self):
        profile = self.get_selected_profile()
        if not profile:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Group")
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Group Name:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(fill="x", padx=20, pady=5)
        name_entry.focus_set()
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Group name cannot be empty")
                return
            for group in profile["groups"]:
                if group["name"] == name:
                    messagebox.showerror("Error", f"Group '{name}' already exists in this profile")
                    return
            profile["groups"].append({
                "name": name,
                "buttons": []
            })
            self.refresh_groups()
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
    
    def rename_group(self):
        profile = self.get_selected_profile()
        if not profile:
            return
        selection = self.group_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(profile["groups"]):
            return
        group = profile["groups"][index]
        old_name = group["name"]
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Group")
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="New Group Name:").pack(pady=(10, 0))
        name_var = tk.StringVar(value=old_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(fill="x", padx=20, pady=5)
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Group name cannot be empty")
                return
            if name != old_name:
                for g in profile["groups"]:
                    if g["name"] == name:
                        messagebox.showerror("Error", f"Group '{name}' already exists in this profile")
                        return
                group["name"] = name
                if self.config_data["active_group"] == old_name:
                    self.config_data["active_group"] = name
                self.refresh_groups()
            dialog.destroy()
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
    
    def delete_group(self):
        profile = self.get_selected_profile()
        if not profile:
            return
        selection = self.group_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(profile["groups"]):
            return
        if len(profile["groups"]) <= 1:
            messagebox.showerror("Error", "Cannot delete the last group in a profile")
            return
        group = profile["groups"][index]
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the group '{group['name']}'?"):
            del profile["groups"][index]
            if self.config_data["active_group"] == group["name"]:
                self.config_data["active_group"] = profile["groups"][0]["name"]
            self.refresh_groups()
    
    def add_button(self):
        group = self.get_selected_group()
        if not group:
            return
        self.current_button_index = None
        self.enable_editor()
        self.button_text.delete(0, tk.END)
        self.button_text.insert(0, "New Button")
        self.bg_color.delete(0, tk.END)
        self.bg_color.insert(0, "#3498db")
        self.text_color.delete(0, tk.END)
        self.text_color.insert(0, "#ffffff")
        self.image_url.delete(0, tk.END)
        self.is_toggle.set(False)
        self.sequence_data = [['f1']]
        self.refresh_sequences()
        self.button_text.focus_set()
        self.button_text.select_range(0, tk.END)
    
    def duplicate_button(self):
        button = self.get_selected_button()
        if not button:
            return
        group = self.get_selected_group()
        new_button = button.copy()
        new_button["text"] = f"{button['text']} (Copy)"
        group["buttons"].append(new_button)
        self.refresh_buttons()
    
    def delete_button(self):
        group = self.get_selected_group()
        if not group:
            return
        selection = self.buttons_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this button?"):
            del group["buttons"][index]
            self.refresh_buttons()
            self.disable_editor()
    
    def save_button(self):
        group = self.get_selected_group()
        if not group:
            return
        text = self.button_text.get().strip()
        if not text:
            messagebox.showerror("Error", "Button text cannot be empty")
            return
        bg_color = self.bg_color.get().strip()
        if not bg_color:
            bg_color = "#3498db"
        text_color = self.text_color.get().strip()
        if not text_color:
            text_color = "#ffffff"
        image_url = self.image_url.get().strip()
        if not image_url:
            image_url = None
        is_toggle = self.is_toggle.get()
        if not self.sequence_data:
            messagebox.showerror("Error", "Button must have at least one key combination")
            return
        button_data = {
            "text": text,
            "color": bg_color,
            "text_color": text_color,
            "image": image_url,
            "hotkey": self.sequence_data[0],
            "is_toggle": is_toggle
        }
        if len(self.sequence_data) > 1:
            button_data["sequence"] = self.sequence_data[1:]
        if self.current_button_index is not None and self.current_button_index < len(group["buttons"]):
            group["buttons"][self.current_button_index] = button_data
        else:
            group["buttons"].append(button_data)
        self.refresh_buttons()
        self.disable_editor()
    
    def cancel_edit(self):
        self.disable_editor()
    
    def save_all(self):
        save_config(self.config_data)
        messagebox.showinfo("Success", "Configuration has been saved successfully!")
        global config
        config = load_config()
    
    def run(self):
        self.root.mainloop()

def start_button_manager():
    manager = ButtonManager()
    manager.run()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MobileDeck</title>
    <style>
        :root {
            --bg-color: #121212;
            --text-color: #ffffff;
            --button-border: rgba(255, 255, 255, 0.8);
            --toggle-bg: #333;
            --toggle-dot: #fff;
            --settings-bg: rgba(30, 30, 30, 0.9);
        }
        [data-theme="light"] {
            --bg-color: #f5f5f5;
            --text-color: #121212;
            --button-border: rgba(0, 0, 0, 0.8);
            --toggle-bg: #ccc;
            --toggle-dot: #333;
            --settings-bg: rgba(240, 240, 240, 0.9);
        }
        body {
            margin: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        .header {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 10px 20px;
            background-color: var(--bg-color);
            border-bottom: 1px solid var(--button-border);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 50;
            height: 60px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        .logo {
            height: 40px;
            width: 192px;
        }
        .theme-toggle {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
            margin-left: 10px;
        }
        .theme-toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--toggle-bg);
            transition: .4s;
            border-radius: 34px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 4px;
            bottom: 4px;
            background-color: var(--toggle-dot);
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider {
            background-color: #2196F3;
        }
        input:checked + .slider:before {
            transform: translateX(26px);
        }
        .buttons-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: flex-start;
            padding: 20px;
            flex-grow: 1;
            margin-top: 70px;
        }
        .group-selector {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            margin-bottom: 20px;
        }
        .group-selector select {
            background-color: var(--bg-color);
            color: var(--text-color);
            border: 1px solid var(--button-border);
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 16px;
            margin: 0 10px;
        }
        .button {
            display: flex;
            justify-content: center;
            align-items: center;
            width: {{ button_width }}px;
            height: {{ button_height }}px;
            margin: 10px;
            border: 2px solid var(--button-border);
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            text-align: center;
            text-transform: uppercase;
            position: relative;
            transition: all 0.2s ease;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .button:active:not(.toggle-button.active) {
            transform: scale(0.95);
            opacity: 0.8;
        }
        .button .image-container {
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
            border-radius: 8px;
            z-index: 0;
        }
        .button img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0.6;
        }
        .button .text {
            z-index: 1;
            position: relative;
            padding: 8px;
            text-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
        }
        .toggle-button {
            border-style: dashed;
        }
        .toggle-button.active {
            border-style: solid;
            box-shadow: 0 0 10px rgba(33, 150, 243, 0.8);
            transform: scale(0.98);
        }
        .settings-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            z-index: 100;
        }
        .settings-panel {
            position: fixed;
            top: 0;
            right: -300px;
            width: 300px;
            height: 100%;
            background-color: var(--settings-bg);
            box-shadow: -5px 0 15px rgba(0, 0, 0, 0.2);
            transition: right 0.3s ease;
            z-index: 100;
            overflow-y: auto;
            padding: 20px;
            box-sizing: border-box;
        }
        .settings-panel.open {
            right: 0;
        }
        .settings-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .close-settings {
            font-size: 1.5rem;
            cursor: pointer;
            background: none;
            border: none;
            color: var(--text-color);
        }
        .setting-item {
            margin-bottom: 15px;
        }
        .setting-item label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .setting-item input, .setting-item select {
            width: 100%;
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #ccc;
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        .theme-setting {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .theme-setting-label {
            margin-right: auto;
            font-weight: bold;
        }
        .save-settings {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-top: 15px;
        }
        .btn-manager {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-top: 15px;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 200;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 20px;
            border-radius: 10px;
            max-width: 80%;
            text-align: center;
        }
        .modal-close {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            margin-top: 15px;
            cursor: pointer;
        }
        @media (max-width: 768px) {
            .button {
                width: calc(50% - 20px);
            }
        }
        @media (max-width: 480px) {
            .button {
                width: calc(100% - 20px);
            }
        }
    </style>
</head>
<body data-theme="{{ theme }}">
    <div class="header">
        <img class="logo" src="/assets/{{ 'MDLight.png' if theme == 'light' else 'MDDark.png' }}" alt="MobileDeck Logo">
    </div>
    <div class="buttons-container">
        <div class="group-selector">
            <select id="profile-select">
                {% for profile in profiles %}
                <option value="{{ profile.name }}" {% if profile.name == active_profile %}selected{% endif %}>{{ profile.name }}</option>
                {% endfor %}
            </select>
            <select id="group-select">
                {% for group in active_groups %}
                <option value="{{ group.name }}" {% if group.name == active_group %}selected{% endif %}>{{ group.name }}</option>
                {% endfor %}
            </select>
        </div>
        {% for button in buttons %}
        <div class="button{% if button.get('is_toggle', False) %} toggle-button{% endif %}" 
             style="background-color: {{ button['color'] }}; color: {{ button['text_color'] }};" 
             data-hotkey='{{ button["hotkey"]|tojson }}'
             {% if button.get('sequence', False) %}data-sequence='{{ button["sequence"]|tojson }}'{% endif %}
             data-id="{{ loop.index0 }}"
             {% if button.get('is_toggle', False) %}data-is-toggle="true"{% endif %}>
            {% if button['image'] %}
            <div class="image-container">
                <img src="{{ button['image'] }}" alt="Button Image">
            </div>
            {% endif %}
            <div class="text">{{ button['text'] }}</div>
        </div>
        {% endfor %}
    </div>
    <button class="settings-button" id="settings-button">⚙️</button>
    <div class="settings-panel" id="settings-panel">
        <div class="settings-title">
            <span>Settings</span>
            <button class="close-settings" id="close-settings">×</button>
        </div>
        <div class="theme-setting">
            <span class="theme-setting-label">Light Mode</span>
            <label class="theme-toggle">
                <input type="checkbox" id="theme-switch" {% if theme == 'light' %}checked{% endif %}>
                <span class="slider"></span>
            </label>
        </div>
        <div class="setting-item">
            <label for="buttons-per-row">Buttons Per Row</label>
            <input type="number" id="buttons-per-row" min="1" max="6" value="{{ buttons_per_row }}">
        </div>
        <div class="setting-item">
            <label for="button-height">Button Height (px)</label>
            <input type="number" id="button-height" min="50" max="300" value="{{ button_height }}">
        </div>
        <div class="setting-item">
            <label for="button-width">Button Width (px)</label>
            <input type="number" id="button-width" min="50" max="400" value="{{ button_width }}">
        </div>
        <button class="save-settings" id="save-settings">Save Settings</button>
        <button class="btn-manager" id="btn-manager">Button Management</button>
    </div>
    <div class="modal" id="manager-modal" style="display: none;">
        <div class="modal-content">
            <h2>Button Management</h2>
            <p>Button management interface has been opened on your PC.</p>
            <p>You can create, edit, and organize your buttons there.</p>
            <button class="modal-close" id="modal-close">Close</button>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const themeSwitch = document.getElementById('theme-switch');
            const profileSelect = document.getElementById('profile-select');
            const groupSelect = document.getElementById('group-select');
            const btnManager = document.getElementById('btn-manager');
            const managerModal = document.getElementById('manager-modal');
            const modalClose = document.getElementById('modal-close');
            themeSwitch.addEventListener('change', () => {
                const logo = document.querySelector('.logo');
                if (themeSwitch.checked) {
                    document.body.setAttribute('data-theme', 'light');
                    saveThemePreference('light');
                    if (logo) {
                        logo.src = '/assets/MDLight.png';
                    }
                } else {
                    document.body.setAttribute('data-theme', 'dark');
                    saveThemePreference('dark');
                    if (logo) {
                        logo.src = '/assets/MDDark.png';
                    }
                }
            });
            function saveThemePreference(theme) {
                fetch('/set_theme', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ theme: theme })
                });
            }
            profileSelect.addEventListener('change', () => {
                window.location.href = `/set_profile/${profileSelect.value}`;
            });
            groupSelect.addEventListener('change', () => {
                window.location.href = `/set_group/${groupSelect.value}`;
            });
            btnManager.addEventListener('click', () => {
                fetch('/open_button_manager')
                    .then(response => {
                        if (response.ok) {
                            managerModal.style.display = 'flex';
                        }
                    });
            });
            modalClose.addEventListener('click', () => {
                managerModal.style.display = 'none';
            });
            const buttons = document.querySelectorAll('.button');
            buttons.forEach(button => {
                const buttonId = button.getAttribute('data-id');
                const isToggle = button.getAttribute('data-is-toggle') === 'true';
                if (isToggle) {
                    fetch(`/get_button_state/${buttonId}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.state) {
                                button.classList.add('active');
                            }
                        });
                }
                button.addEventListener('click', () => {
                    const hotkey = JSON.parse(button.getAttribute('data-hotkey') || '[]');
                    const sequence = JSON.parse(button.getAttribute('data-sequence') || 'null');
                    const isToggle = button.getAttribute('data-is-toggle') === 'true';
                    const buttonId = button.getAttribute('data-id');
                    if (isToggle) {
                        const isActive = button.classList.toggle('active');
                        fetch('/set_button_state', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ 
                                id: buttonId,
                                state: isActive
                            })
                        });
                    }
                    fetch('/trigger', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            hotkey: hotkey,
                            sequence: sequence,
                            toggle: isToggle,
                            id: buttonId
                        })
                    }).then(response => {
                        if (!response.ok) {
                            console.error("Failed to send hotkey to server:", response.status, response.statusText);
                        }
                    }).catch(error => {
                        console.error("Error sending hotkey to server:", error);
                    });
                });
            });
            const settingsButton = document.getElementById('settings-button');
            const settingsPanel = document.getElementById('settings-panel');
            const closeSettings = document.getElementById('close-settings');
            const saveSettings = document.getElementById('save-settings');
            settingsButton.addEventListener('click', () => {
                settingsPanel.classList.add('open');
            });
            closeSettings.addEventListener('click', () => {
                settingsPanel.classList.remove('open');
            });
            saveSettings.addEventListener('click', () => {
                const buttonsPerRow = document.getElementById('buttons-per-row').value;
                const buttonHeight = document.getElementById('button-height').value;
                const buttonWidth = document.getElementById('button-width').value;
                fetch('/save_settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        buttons_per_row: buttonsPerRow,
                        button_height: buttonHeight,
                        button_width: buttonWidth
                    })
                }).then(response => {
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        console.error("Failed to save settings");
                    }
                });
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    theme = session.get('theme', 'dark')
    buttons_per_row = session.get('buttons_per_row', 3)
    button_height = session.get('button_height', 100)
    button_width = session.get('button_width', 120)
    active_profile = getattr(config, 'active_profile', 'Default')
    active_group = getattr(config, 'active_group', 'Main')
    active_groups = []
    buttons = []
    for profile in config.profiles:
        if profile['name'] == active_profile:
            active_groups = profile['groups']
            for group in profile['groups']:
                if group['name'] == active_group:
                    buttons = group['buttons']
                    break
            break
    return render_template_string(
        HTML_TEMPLATE, 
        buttons=buttons,
        profiles=config.profiles,
        active_profile=active_profile,
        active_groups=active_groups,
        active_group=active_group,
        theme=theme,
        buttons_per_row=buttons_per_row,
        button_height=button_height,
        button_width=button_width
    )

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/set_theme', methods=['POST'])
def set_theme():
    data = request.get_json()
    theme = data.get('theme', 'dark')
    session['theme'] = theme
    return '', 204

@app.route('/set_profile/<profile_name>')
def set_profile(profile_name):
    for profile in config.profiles:
        if profile['name'] == profile_name:
            config.active_profile = profile_name
            config.active_group = profile['groups'][0]['name']
            config_data = {
                "profiles": config.profiles,
                "default_preferences": config.default_preferences,
                "active_profile": profile_name,
                "active_group": profile['groups'][0]['name']
            }
            save_config(config_data)
            break
    return redirect(url_for('index'))

@app.route('/set_group/<group_name>')
def set_group(group_name):
    active_profile = config.active_profile
    for profile in config.profiles:
        if profile['name'] == active_profile:
            for group in profile['groups']:
                if group['name'] == group_name:
                    config.active_group = group_name
                    config_data = {
                        "profiles": config.profiles,
                        "default_preferences": config.default_preferences,
                        "active_profile": active_profile,
                        "active_group": group_name
                    }
                    save_config(config_data)
                    break
    return redirect(url_for('index'))

@app.route('/trigger', methods=['POST'])
def trigger():
    data = request.get_json()
    if not data:
        return 'Bad Request', 400
    hotkey = data.get('hotkey', [])
    sequence = data.get('sequence', None)
    is_toggle = data.get('toggle', False)
    button_id = data.get('id')
    try:
        if is_toggle and not button_states.get(button_id, False):
            return '', 204
        if hotkey:
            for key in hotkey:
                key_to_press = getattr(Key, key, key) if hasattr(Key, key) else key
                keyboard.press(key_to_press)
            for key in reversed(hotkey):
                key_to_press = getattr(Key, key, key) if hasattr(Key, key) else key
                keyboard.release(key_to_press)
        if sequence:
            for step in sequence:
                for key in step:
                    key_to_press = getattr(Key, key, key) if hasattr(Key, key) else key
                    keyboard.press(key_to_press)
                for key in reversed(step):
                    key_to_press = getattr(Key, key, key) if hasattr(Key, key) else key
                    keyboard.release(key_to_press)
    except Exception as e:
        print(f"Error while processing keys: {e}")
        return 'Error', 500
    return '', 204

@app.route('/set_button_state', methods=['POST'])
def set_button_state():
    data = request.get_json()
    button_id = data.get('id')
    state = data.get('state', False)
    if button_id is not None:
        button_states[button_id] = state
    return '', 204

@app.route('/get_button_state/<button_id>')
def get_button_state(button_id):
    state = button_states.get(button_id, False)
    return jsonify({'state': state})

@app.route('/save_settings', methods=['POST'])
def save_settings():
    data = request.get_json()
    buttons_per_row = int(data.get('buttons_per_row', 3))
    button_height = int(data.get('button_height', 100))
    button_width = int(data.get('button_width', 120))
    session['buttons_per_row'] = buttons_per_row
    session['button_height'] = button_height
    session['button_width'] = button_width
    return '', 204

@app.route('/open_button_manager')
def open_button_manager():
    thread = threading.Thread(target=start_button_manager)
    thread.daemon = True
    thread.start()
    return '', 204

if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists('assets'):
        os.makedirs('assets')
        print("Created 'assets' directory. Please place MDDark.png and MDLight.png files there.")
    config = load_config()
    for profile in config.profiles:
        if profile["name"] == config.active_profile:
            for group in profile["groups"]:
                if group["name"] == config.active_group:
                    for i, button in enumerate(group["buttons"]):
                        if button.get('is_toggle', False):
                            button_states[str(i)] = False
    app.run(host='0.0.0.0', port=23843, debug=True)