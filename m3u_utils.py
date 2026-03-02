import requests
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox

from m3u_processor import load_m3u, parse_m3u, save_m3u
from url_manager import (
    extract_username,
    fetch_m3u_content,
    generate_m3u_filename,
    load_urls_from_text,
    process_urls,
    save_urls_to_m3u,
)


class M3UHandler:
    def __init__(self, app):
        self.app = app
        self.lines = None
        self.groups = {}
        self.remove_groups = set()
        self.remove_channels = {}
        self.pin_channels = {}
        self.urls = self.m3u_urls = self.stream_urls = None
        self._undo_snapshot = None

    def _status(self, text):
        if hasattr(self.app, "set_status"):
            self.app.set_status(text)

    def _log(self, text, level="INFO"):
        if hasattr(self.app, "log"):
            self.app.log(text, level=level)

    def _capture_undo(self, action_name):
        self._undo_snapshot = {
            "action": action_name,
            "remove_groups": set(self.remove_groups),
            "remove_channels": deepcopy(self.remove_channels),
            "pin_channels": deepcopy(self.pin_channels),
            "group": self.app.group_var.get() if hasattr(self.app, "group_var") else "",
            "search": self.app.channel_search_var.get() if hasattr(self.app, "channel_search_var") else "",
        }

    def undo_last_action(self):
        if not self._undo_snapshot:
            self._status("Nu exista actiune pentru undo")
            self._log("Undo ignorat: nu exista snapshot anterior", level="WARN")
            return

        snap = self._undo_snapshot
        self.remove_groups = set(snap["remove_groups"])
        self.remove_channels = deepcopy(snap["remove_channels"])
        self.pin_channels = deepcopy(snap["pin_channels"])

        if hasattr(self.app, "channel_search_var"):
            self.app.channel_search_var.set(snap["search"])
        if hasattr(self.app, "group_var"):
            self.app.group_var.set(snap["group"])
        if hasattr(self.app, "restore_view_from_model"):
            self.app.restore_view_from_model()
        if hasattr(self.app, "notebook"):
            self.app.notebook.select(1)

        self._status(f"Undo: {snap['action']}")
        self._log(f"Undo aplicat pentru actiunea: {snap['action']}")
        self._undo_snapshot = None

    def download_iptv(self, entries):
        full_url = entries["URL Complet"].get()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        http_url = full_url.replace("https://", "http://")
        try:
            response = requests.get(http_url, timeout=30, headers=headers, verify=False)
            response.raise_for_status()
            content = response.content
        except requests.RequestException as e:
            try:
                response = requests.get(full_url, timeout=30, headers=headers, verify=False)
                response.raise_for_status()
                content = response.content
            except requests.RequestException as e2:
                error_msg = (
                    f"Nu am putut descarca:\n"
                    f"HTTP: {http_url}\nEroare: {e}\n"
                    f"HTTPS: {full_url}\nEroare: {e2}"
                )
                if hasattr(e2, "response") and e2.response is not None:
                    error_msg += f"\nCod HTTP: {e2.response.status_code}"
                messagebox.showerror("Eroare", error_msg)
                self._status("Eroare la descarcare IPTV")
                self._log("Download IPTV esuat", level="ERROR")
                return

        save_path = filedialog.asksaveasfilename(defaultextension=".m3u", filetypes=[("M3U files", "*.m3u")])
        if save_path:
            with open(save_path, "wb") as f:
                f.write(content)
            messagebox.showinfo("Succes", f"Lista descarcata la: {save_path}")
            self._status(f"Lista descarcata: {Path(save_path).name}")
            self._log(f"Lista IPTV descarcata: {Path(save_path).name}")
            self.load_file(save_path, switch_tab=True)

    def load_file(self, file_path=None, switch_tab=False):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[("M3U files", "*.m3u")])
        if file_path:
            self.lines = load_m3u(file_path)
            self.groups = parse_m3u(self.lines)
            self.remove_groups.clear()
            self.remove_channels.clear()
            self.pin_channels.clear()
            self.app.file_label.config(text=f"Incarcat: {Path(file_path).name}")
            self._status(f"Fisier incarcat: {Path(file_path).name}")
            self._log(f"Fisier M3U incarcat: {Path(file_path).name}")
            if hasattr(self.app, "refresh_conflicts_panel"):
                self.app.refresh_conflicts_panel()
            if self.groups:
                self.app.group_dropdown["values"] = list(self.groups.keys())
                if not self.app.group_var.get():
                    self.app.group_var.set(list(self.groups.keys())[0])
                    if hasattr(self.app, "channel_search_var"):
                        self.app.channel_search_var.set("")
                    self.update_channels(list(self.groups.keys())[0])
                if switch_tab:
                    self.app.notebook.select(1)
            else:
                messagebox.showerror("Eroare", "Fisierul M3U nu contine grupuri valide.")
                self._status("Eroare: fisier M3U invalid")
                self._log("Fisier M3U invalid", level="ERROR")
                self.app.channel_listbox.delete(0, "end")
                self.app.group_var.set("")
                self.app.group_dropdown.set("")

    def update_channels(self, group):
        if group and group in self.groups and group not in self.remove_groups and self.app.group_var.get():
            if hasattr(self.app, "refresh_channel_list"):
                self.app.refresh_channel_list(group)
            else:
                self.app.channel_listbox.delete(0, "end")
                for name, _, _ in self.groups[group]:
                    if name not in self.remove_channels.get(group, []):
                        self.app.channel_listbox.insert("end", name)
                        if group in self.pin_channels and name in self.pin_channels[group]:
                            self.app.channel_listbox.itemconfig("end", {"fg": "#00ff00"})
                self.app.group_var.set(group)
        else:
            self.app.channel_listbox.delete(0, "end")
            self.app.group_var.set("")
            self.app.group_dropdown.set("")

    def remove_selected(self):
        group = self.app.group_var.get()
        if not group or group not in self.groups or group in self.remove_groups:
            return

        selected = self.app.channel_listbox.curselection()
        self.app.group_dropdown.configure(state="disabled")

        if not selected:
            if not messagebox.askyesno("Confirmare", f"Stergi complet grupul '{group}'?"):
                self.app.group_dropdown.configure(state="normal")
                return

            self._capture_undo(f"Stergere grup {group}")
            self.remove_groups.add(group)
            remaining_groups = [g for g in self.groups.keys() if g not in self.remove_groups]
            self.app.group_dropdown["values"] = remaining_groups
            self.app.channel_listbox.delete(0, "end")
            self.app.group_var.set("")
            self.app.group_dropdown.set("")
            self.app.group_dropdown.configure(state="normal")
            self._status(f"Grup sters: {group}")
            self._log(f"Grup sters: {group}", level="WARN")
            if hasattr(self.app, "refresh_conflicts_panel"):
                self.app.refresh_conflicts_panel()
            return

        if not messagebox.askyesno("Confirmare", f"Stergi {len(selected)} canal(e) din '{group}'?"):
            self.app.group_dropdown.configure(state="normal")
            return

        self._capture_undo(f"Stergere canale din {group}")
        for idx in sorted(selected, reverse=True):
            name = self.app.channel_listbox.get(idx)
            self.remove_channels.setdefault(group, []).append(name)
            self.app.channel_listbox.delete(idx)

        remaining_channels = [ch for ch in self.groups[group] if ch[0] not in self.remove_channels.get(group, [])]
        if not remaining_channels:
            self.remove_groups.add(group)
            remaining_groups = [g for g in self.groups.keys() if g not in self.remove_groups]
            self.app.group_dropdown["values"] = remaining_groups
            self.app.channel_listbox.delete(0, "end")
            self.app.group_var.set("")
            self.app.group_dropdown.set("")

        self.app.group_dropdown.configure(state="normal")
        self._status(f"Canale sterse din grup: {group}")
        self._log(f"Canale sterse din grup: {group}", level="WARN")
        if hasattr(self.app, "refresh_conflicts_panel"):
            self.app.refresh_conflicts_panel()

    def pin_selected(self):
        group = self.app.group_var.get()
        if not group or group not in self.groups or group in self.remove_groups:
            return

        selected = self.app.channel_listbox.curselection()
        if not selected:
            self._status("Selecteaza cel putin un canal pentru PIN")
            self._log("PIN selectat ignorat: fara selectie", level="WARN")
            return

        self._capture_undo(f"PIN pe canale in {group}")
        for idx in selected:
            name = self.app.channel_listbox.get(idx)
            self.pin_channels.setdefault(group, [])
            if name not in self.pin_channels[group]:
                self.pin_channels[group].append(name)
            self.app.channel_listbox.itemconfig(idx, {"fg": "#00ff00"})

        if hasattr(self.app, "refresh_channel_list"):
            self.app.refresh_channel_list(group)
        self._status(f"PIN adaugat in grup: {group}")
        self._log(f"PIN adaugat pe selectie in grup: {group}")

    def pin_group(self):
        group = self.app.group_var.get()
        if not group or group not in self.groups or group in self.remove_groups:
            return

        self._capture_undo(f"PIN pe grup {group}")
        self.pin_channels[group] = [
            name for name, _, _ in self.groups[group] if name not in self.remove_channels.get(group, [])
        ]
        self.update_channels(group)
        self._status(f"PIN aplicat pe grup: {group}")
        self._log(f"PIN aplicat pe tot grupul: {group}")

    def save_file(self):
        output_file = filedialog.asksaveasfilename(defaultextension=".m3u", filetypes=[("M3U files", "*.m3u")])
        if output_file:
            save_m3u(
                self.lines,
                self.groups,
                self.remove_groups,
                self.remove_channels,
                self.pin_channels,
                self.app.pin_entry.get(),
                output_file,
            )
            messagebox.showinfo("Succes", f"Fisier salvat: {output_file}")
            self._status(f"Fisier salvat: {Path(output_file).name}")
            self._log(f"Fisier M3U salvat: {Path(output_file).name}")

    def load_text_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            self.urls = load_urls_from_text(file_path)
            self.m3u_urls, self.stream_urls = process_urls(self.urls)
            self.app.url_tree.delete(*self.app.url_tree.get_children())
            for url in self.m3u_urls:
                username = extract_username(url)
                self.app.url_tree.insert("", "end", values=("M3U", url, username))
            for url in self.stream_urls:
                username = extract_username(url)
                self.app.url_tree.insert("", "end", values=("Stream", url, username))
            self.app.url_label.config(
                text=(
                    f"Incarcat: {Path(file_path).name} "
                    f"({len(self.m3u_urls)} liste M3U, {len(self.stream_urls)} stream-uri)"
                )
            )
            self._status(f"URL text incarcat: {Path(file_path).name}")
            self._log(f"Fisier URL text incarcat: {Path(file_path).name}")

    def save_urls_as_m3u(self):
        if not self.m3u_urls and not self.stream_urls:
            messagebox.showerror("Eroare", "Incarca un fisier text cu URL-uri mai intai!")
            self._status("Eroare: nu exista URL-uri de salvat")
            self._log("Salvare URL-uri anulata: lipsesc date", level="ERROR")
            return

        save_dir = filedialog.askdirectory(title="Alege folderul unde sa salvezi listele")
        if save_dir:
            for url in self.m3u_urls:
                content = fetch_m3u_content(url)
                if content:
                    output_file = Path(save_dir) / generate_m3u_filename(url)
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(content))
            if self.stream_urls:
                output_file = Path(save_dir) / "stream_urls_importate.m3u"
                save_urls_to_m3u(self.stream_urls, output_file)
            messagebox.showinfo("Succes", f"Listele salvate in: {save_dir}")
            self._status(f"Liste salvate in: {save_dir}")
            self._log(f"Liste URL salvate in folder: {save_dir}")
