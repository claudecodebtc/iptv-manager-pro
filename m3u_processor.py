import re


def load_m3u(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.readlines()


def parse_m3u(lines):
    groups = {}
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line.startswith("#EXTINF"):
            continue

        group_match = re.search(r'group-title="([^"]+)"', line)
        group = group_match.group(1) if group_match else "Fara grup"
        name = line.split(",", 1)[-1].strip() if "," in line else "Unnamed"

        # Find the first non-empty, non-comment line after EXTINF as stream URL.
        url = ""
        j = i + 1
        while j < len(lines):
            candidate = lines[j].strip()
            if not candidate or candidate.startswith("#"):
                j += 1
                continue
            url = candidate
            break

        if not url:
            continue

        groups.setdefault(group, []).append((name, url, i))
    return groups


def save_m3u(lines, groups, remove_groups, remove_channels, pin_channels, pin, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, raw in enumerate(lines):
            line = raw.strip()
            if line.startswith("#EXTINF"):
                group_match = re.search(r'group-title="([^"]+)"', line)
                group = group_match.group(1) if group_match else "Fara grup"
                if group in remove_groups:
                    continue
                for name, url, orig_idx in groups.get(group, []):
                    if orig_idx == i:
                        if name in remove_channels.get(group, []):
                            break
                        new_line = line
                        if name in pin_channels.get(group, []) and 'parent-code="' not in line:
                            new_line = line.replace(
                                f'group-title="{group}"',
                                f'group-title="{group}" parent-code="{pin}"',
                            )
                        f.write(f"{new_line}\n{url}\n")
                        break
            elif not any(line == url for g in groups.values() for _, url, _ in g):
                f.write(f"{line}\n")
