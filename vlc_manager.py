import subprocess
import requests
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox

class VLCManager:
    def __init__(self, vlc_path):
        self.vlc_path = vlc_path
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def play_in_vlc(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        url = tree.item(selected[0])['values'][1]
        if not url.lower().startswith(('http://', 'https://')):
            messagebox.showwarning("Atenție", "Selectează un URL valid (http/https)!")
            return
        self._play_url(url)

    def play_stream_direct(self, tree):
        selected = tree.selection()
        if not selected:
            return
        url = tree.item(selected[0])['values'][1]
        if not url.lower().startswith(('http://', 'https://')):
            messagebox.showwarning("Atenție", "Selectează un URL valid (http/https)!")
            return
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=15)
            if response.status_code != 200:
                messagebox.showerror("Eroare", f"Link-ul nu e valid: {response.status_code}")
                return
            stream_url = next((line for line in response.text.splitlines() if line.startswith('http')), None)
            if stream_url:
                self._play_url(stream_url, autostart=True)
            else:
                messagebox.showwarning("Atenție", "Nu am găsit un stream direct în M3U!")
        except requests.RequestException as e:
            messagebox.showerror("Eroare", f"Nu pot testa stream-ul: {str(e)}")

    def choose_channel(self, tree):
        selected = tree.selection()
        if not selected:
            return
        url = tree.item(selected[0])['values'][1]
        if not url.lower().startswith(('http://', 'https://')):
            messagebox.showwarning("Atenție", "Selectează un URL valid (http/https)!")
            return
        
        channels = self._parse_m3u(url)
        if not channels:
            return

        window = tk.Toplevel(bg="#1e1e2f")
        window.title("Alege Canal")
        window.geometry("700x600")

        filter_frame = ttk.Frame(window)
        ttk.Label(filter_frame, text="Filtrează grup:").pack(side=tk.LEFT, padx=10)
        group_var = tk.StringVar()
        groups = sorted(set(ch[3] for ch in channels))
        ttk.OptionMenu(filter_frame, group_var, groups[0], *groups).pack(side=tk.LEFT, padx=10)
        filter_frame.pack(pady=15)

        channel_tree = ttk.Treeview(window, columns=("Nume", "Grup", "Status"), show="headings", height=20)
        channel_tree.heading("Nume", text="Nume Canal")
        channel_tree.heading("Grup", text="Grup")
        channel_tree.heading("Status", text="Status")
        channel_tree.column("Nume", width=350)
        channel_tree.column("Grup", width=200)
        channel_tree.column("Status", width=100)
        
        def update_tree(*args):
            channel_tree.delete(*channel_tree.get_children())
            selected_group = group_var.get()
            for name, _, status, group in channels:
                if selected_group == group or selected_group == groups[0]:
                    channel_tree.insert("", "end", values=(name, group, status))
        
        group_var.trace("w", update_tree)
        update_tree()
        channel_tree.pack(pady=15)

        ttk.Button(window, text="Redă", command=lambda: self._play_selected(channel_tree, channels, window)).pack(pady=15)

    def load_group(self, tree):
        selected = tree.selection()
        if not selected:
            return
        url = tree.item(selected[0])['values'][1]
        if not url.lower().startswith(('http://', 'https://')):
            messagebox.showwarning("Atenție", "Selectează un URL valid (http/https)!")
            return
        
        groups = self._parse_m3u_groups(url)
        if not groups:
            return

        window = tk.Toplevel(bg="#1e1e2f")
        window.title("Alege Grup")
        window.geometry("500x400")

        group_listbox = tk.Listbox(window, height=15, width=50, font=("Segoe UI", 10), bg="#2d2d44", fg="#ffffff", selectbackground="#57578a")
        for group in sorted(groups.keys()):
            group_listbox.insert(tk.END, f"{group} ({len(groups[group])} canale)")
        group_listbox.pack(pady=15)

        ttk.Button(window, text="Încarcă Grup", command=lambda: self._load_selected_group(group_listbox, groups, window)).pack(pady=15)

    def _play_url(self, url, autostart=False):
        command = [self.vlc_path, "--one-instance", "--playlist-enqueue", "--verbose", "2"]
        if autostart:
            command.append("--playlist-autostart")
        command.append(url)
        try:
            subprocess.Popen(command)
            messagebox.showinfo("VLC", f"Trimis la VLC: {url}\nVerifică playlist-ul (Ctrl+L)!")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu pot rula VLC: {str(e)}")

    def _parse_m3u(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=15)
            if response.status_code != 200:
                messagebox.showerror("Eroare", f"Link-ul nu e valid: {response.status_code}")
                return []
            lines = response.text.splitlines()
            channels = []
            current_name = current_group = None
            for line in lines:
                if line.startswith('#EXTINF:'):
                    current_name = line.split(',')[-1].strip()
                    current_group = line.split('group-title="')[1].split('"')[0] if 'group-title="' in line else "Fără grup"
                elif line.startswith('http'):
                    if current_name:
                        status = self._check_stream(line)
                        channels.append((current_name, line, status, current_group))
                        current_name = None
            if not channels:
                messagebox.showwarning("Atenție", "Nu am găsit canale în M3U!")
            return channels
        except requests.RequestException as e:
            messagebox.showerror("Eroare", f"Nu pot încărca M3U: {str(e)}")
            return []

    def _parse_m3u_groups(self, url):
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=15)
            if response.status_code != 200:
                messagebox.showerror("Eroare", f"Link-ul nu e valid: {response.status_code}")
                return {}
            lines = response.text.splitlines()
            groups = {}
            current_name = current_group = None
            for line in lines:
                if line.startswith('#EXTINF:'):
                    current_name = line.split(',')[-1].strip()
                    current_group = line.split('group-title="')[1].split('"')[0] if 'group-title="' in line else "Fără grup"
                elif line.startswith('http'):
                    if current_name:
                        if current_group not in groups:
                            groups[current_group] = []
                        groups[current_group].append((current_name, line))
                        current_name = None
            return groups
        except requests.RequestException as e:
            messagebox.showerror("Eroare", f"Nu pot încărca M3U: {str(e)}")
            return {}

    def _check_stream(self, url):
        try:
            response = requests.head(url, headers=self.headers, verify=False, timeout=5)
            return response.status_code
        except requests.RequestException as e:
            return f"Eroare: {str(e)}"

    def _play_selected(self, tree, channels, window):
        sel = tree.selection()
        if sel:
            index = tree.index(sel[0])
            _, stream_url, status, _ = channels[index]
            if str(status) != "200":
                messagebox.showwarning("Atenție", f"Stream-ul nu e accesibil: {status}")
                return
            self._play_url(stream_url, autostart=True)
            window.destroy()

    def _load_selected_group(self, listbox, groups, window):
        sel = listbox.curselection()
        if sel:
            group_name = sorted(groups.keys())[sel[0]]
            filtered_m3u = ["#EXTM3U"]
            for name, stream_url in groups[group_name]:
                filtered_m3u.append(f'#EXTINF:-1 group-title="{group_name}",{name}')
                filtered_m3u.append(stream_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m3u") as tmp_file:
                tmp_file.write("\n".join(filtered_m3u).encode('utf-8'))
                self._play_url(tmp_file.name)
            window.destroy()
