import os
import re
import sys
import time
import subprocess
import logging

IS_WINDOWS = sys.platform.startswith('win')
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    ctypes = None
    wintypes = None
    user32 = None
    kernel32 = None

BM_CLICK = 0x00F5
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_UNCHECKED = 0x0000
BST_CHECKED = 0x0001

LB_GETBUILD = 0x0188
LB_SETCURSEL = 0x0186
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A
LB_GETCOUNT = 0x018B
LB_GETITEMRECT = 0x0198
LB_GETITEMHEIGHT = 0x01A1
LB_ERR = -1

GW_OWNER = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def get_default_paths():
    """Returns candidate paths for FOC48 executable/shortcut and XML parameters."""
    desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
    candidates_foc = [
        r'C:\Users\labhub\Desktop\FOC48_autoOrgan.lnk',
        os.path.join(desktop_dir, 'FOC48_autoOrgan.lnk'),
        r'C:\Users\labhub\Desktop\FOC48_autoOrgan.exe',
        os.path.join(desktop_dir, 'FOC48_autoOrgan.exe'),
        r'C:\labhub\import\FOC48_autoOrgan.exe',
        r'C:\Labhub\Import\FOC48_autoOrgan.exe',
        r'C:\labhub\import\FOC48_20240227.exe',
        r'C:\Labhub\Import\FOC48_20240227.exe',
    ]
    candidates_xml = [
        r'C:\labhub\import\myrPlate.xml',
        r'C:\Labhub\Import\myrPlate.xml',
        r'C:\labhub\import\myrPlate_Stim_0.xml',
        r'C:\Labhub\Import\myrPlate_Stim_0.xml',
    ]

    chosen_foc = next((p for p in candidates_foc if os.path.exists(p)), candidates_foc[0])
    chosen_xml = next((p for p in candidates_xml if os.path.exists(p)), candidates_xml[0])
    return chosen_foc, chosen_xml


def parse_xml_parameters(xml_path=None):
    """
    Reads <duration>, <saveTime>, and <exportPath> from myrPlate.xml using regex
    (safe against non-standard <! ... > comments in myrPlate.xml).
    Defaults to duration=90s, saveTime=60s, exportPath=C:\\labhub\\FOC48_DATA\\2026.
    """
    if not xml_path:
        _, xml_path = get_default_paths()

    params = {
        'duration': 90,
        'saveTime': 60,
        'exportPath': r'C:\labhub\FOC48_DATA\2026'
    }

    if xml_path and os.path.exists(xml_path):
        try:
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            m_dur = re.search(r'<duration>\s*(\d+)\s*</duration>', content, re.IGNORECASE)
            if m_dur:
                params['duration'] = int(m_dur.group(1))
            m_save = re.search(r'<saveTime>\s*(\d+)\s*</saveTime>', content, re.IGNORECASE)
            if m_save:
                params['saveTime'] = int(m_save.group(1))
            m_exp = re.search(r'<exportPath>\s*([^<]+?)\s*</exportPath>', content, re.IGNORECASE)
            if m_exp:
                raw_path = m_exp.group(1).strip().replace('\\\\', '\\')
                params['exportPath'] = raw_path
        except Exception:
            pass

    return params


def get_available_experiments(export_path=None):
    """Returns a list of experiment folder names found in the FOC48 export directory."""
    if not export_path:
        export_path = parse_xml_parameters().get('exportPath', r'C:\labhub\FOC48_DATA\2026')
    if os.path.isdir(export_path):
        try:
            dirs = [d for d in os.listdir(export_path) if os.path.isdir(os.path.join(export_path, d))]
            return sorted(dirs, reverse=True)
        except Exception:
            pass
    return []


def click_screen(x, y):
    """Executes a single physical left mouse click at screen coordinates (x, y)."""
    if not IS_WINDOWS or not user32:
        return
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.1)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def find_windows_by_title(target_substring):
    """Returns a list of (hwnd, title) for visible top-level windows matching the substring."""
    if not IS_WINDOWS or not user32:
        return []

    found = []

    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value
            if target_substring.lower() in title.lower():
                found.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return found


def find_child_controls(parent_hwnd):
    """Enumerates all direct and nested child control HWNDs, classes, texts, and screen rects."""
    if not IS_WINDOWS or not user32:
        return []

    children = []

    def enum_child_cb(hwnd, _):
        buf_text = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf_text, 512)
        buf_cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf_cls, 256)
        text = buf_text.value.strip()
        cls_name = buf_cls.value.strip()
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        children.append({
            'hwnd': hwnd,
            'text': text,
            'class': cls_name,
            'rect': (rect.left, rect.top, rect.right, rect.bottom)
        })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows(parent_hwnd, WNDENUMPROC(enum_child_cb), 0)
    return children


def get_listbox_items(lb_hwnd):
    """Reads all item strings from a Win32 ListBox control."""
    if not IS_WINDOWS or not user32 or not lb_hwnd:
        return []
    items = []
    try:
        count = user32.SendMessageW(lb_hwnd, LB_GETCOUNT, 0, 0)
        if count <= 0 or count > 500:
            return []
        for idx in range(count):
            tlen = user32.SendMessageW(lb_hwnd, LB_GETTEXTLEN, idx, 0)
            buf_size = max(tlen + 4, 256) if tlen > 0 else 256
            buf = ctypes.create_unicode_buffer(buf_size)
            res = user32.SendMessageW(lb_hwnd, LB_GETTEXT, idx, ctypes.byref(buf))
            if res != LB_ERR:
                items.append(buf.value.strip())
            else:
                items.append("")
    except Exception:
        pass
    return items


def click_listbox_row(lb_hwnd, lb_rect, row_idx, logger=None):
    """
    Calculates the exact screen position of row_idx (0-based) inside a Win32 ListBox
    and performs a single physical click on that row so MFC/Win32 fires LBN_SELCHANGE.
    """
    log = logger.info if logger else print
    left, top, right, bottom = lb_rect
    width = max(10, right - left)
    height = max(10, bottom - top)

    # Click ~30% from the left edge of the ListBox (directly over the item text)
    click_x = left + min(90, max(25, int(width * 0.30)))
    click_y = None

    if IS_WINDOWS and user32 and lb_hwnd:
        try:
            item_rect = wintypes.RECT()
            res = user32.SendMessageW(lb_hwnd, LB_GETITEMRECT, int(row_idx), ctypes.byref(item_rect))
            if res != LB_ERR and item_rect.bottom > item_rect.top and 0 <= item_rect.top < height:
                click_y = top + (item_rect.top + item_rect.bottom) // 2
        except Exception:
            click_y = None

        if click_y is None:
            try:
                item_h = user32.SendMessageW(lb_hwnd, LB_GETITEMHEIGHT, 0, 0)
                if item_h <= 0 or item_h > 45:
                    item_h = 16
            except Exception:
                item_h = 16
            click_y = top + 3 + int((row_idx + 0.5) * item_h)
    else:
        click_y = top + 3 + int((row_idx + 0.5) * 16)

    log(f"[FOC48] Clicking ListBox row {row_idx} at screen ({click_x}, {click_y})...")
    click_screen(click_x, click_y)
    return click_x, click_y


def resolve_experiment_index(experiment_query, listbox_items, export_path=None, logger=None):
    """
    Resolves user's experiment selection into a 0-based ListBox row index.
    Supports:
      - '17b' or 'Plate 2' -> searches for '17b', fallback row 0 (1st item)
      - '17a' or 'Plate 1' -> searches for '17a', fallback row 1 (2nd item)
      - 'Row 1' or '1'     -> row 0 (1st item)
      - 'Row 2' or '2'     -> row 1 (2nd item)
      - Any experiment substring (e.g. '20260917b', '[20260917a]', '20260101y_test')
      - Empty or 'A1'      -> row 0 (1st item)
    """
    log = logger.info if logger else print

    # Fallback item list from disk if ListBox text couldn't be read
    candidate_names = [it for it in listbox_items if it]
    if not candidate_names:
        disk_dirs = get_available_experiments(export_path)
        candidate_names = [f"[{d}]" for d in disk_dirs]

    raw = (experiment_query or "").strip()
    raw_low = raw.lower()

    # Default / legacy placeholder 'A1' -> 1st item (index 0)
    if not raw or raw_low == "a1" or raw_low.startswith("row 1") or raw_low == "1":
        log(f"[FOC48] Experiment query '{raw or 'Default'}' -> Selecting Row 0 (1st Experiment).")
        return 0

    if raw_low.startswith("row "):
        m_row = re.search(r'row\s*(\d+)', raw_low)
        if m_row:
            idx = max(0, int(m_row.group(1)) - 1)
            log(f"[FOC48] Experiment query '{raw}' -> Selecting Row {idx}.")
            return idx

    if raw.isdigit():
        idx = max(0, int(raw) - 1)
        log(f"[FOC48] Numeric Experiment query '{raw}' -> Selecting Row {idx} (#{raw} in list).")
        return idx

    # Check explicit Plate 1 / Plate 2 / 17a / 17b shortcuts
    search_token = None
    fallback_idx = 0
    if "17b" in raw_low or "plate 2" in raw_low or "plate2" in raw_low:
        search_token = "17b"
        fallback_idx = 0
    elif "17a" in raw_low or "plate 1" in raw_low or "plate1" in raw_low:
        search_token = "17a"
        fallback_idx = 1
    else:
        # Take the first token if formatted like "20260917b (Custom)"
        search_token = raw.split()[0].strip("[]").lower()

    if search_token and candidate_names:
        # 1. Exact match (ignoring brackets)
        for idx, name in enumerate(candidate_names):
            if name.strip("[]").lower() == search_token:
                log(f"[FOC48] Matched Experiment '{name}' at Row {idx} for query '{raw}'.")
                return idx
        # 2. Substring match
        for idx, name in enumerate(candidate_names):
            if search_token in name.lower():
                log(f"[FOC48] Matched Experiment '{name}' at Row {idx} (substring '{search_token}').")
                return idx

    log(f"[FOC48] Experiment '{raw}' not found in {candidate_names}; using fallback Row {fallback_idx}.")
    return fallback_idx


def get_window_pid(hwnd):
    """Returns the Windows Process ID (PID) that owns the given HWND."""
    if not IS_WINDOWS or not user32 or not hwnd:
        return None
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value if pid.value else None


def is_process_running(pid):
    """Checks whether a Windows process with the given PID is still active."""
    if not IS_WINDOWS or not kernel32 or not pid:
        return False
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not h_proc:
        return False
    try:
        exit_code = wintypes.DWORD(0)
        if kernel32.GetExitCodeProcess(h_proc, ctypes.byref(exit_code)):
            return exit_code.value == STILL_ACTIVE
        return False
    finally:
        kernel32.CloseHandle(h_proc)


def handle_save_dialog(experiment_query="", logger=None, timeout=45.0, init_delay=5.0):
    """
    Waits for the FOC48 'Save' dialog to appear and stabilize, then:
      1. Selects the target Experiment in the left ListBox (e.g. [20260917b] or [20260917a]).
      2. Waits 1.2s for the Measurement ListBox to populate, then selects the 1st Measurement.
      3. Ensures 'autoClose' is checked (without double-toggling!).
      4. Clicks 'Save All' once (single click only!).
    Returns (success: bool, foc_pid: int | None, main_hwnd: int | None).
    """
    log = logger.info if logger else print
    log_err = logger.error if logger else print

    if not IS_WINDOWS:
        log(f"[FOC48] Non-Windows OS: Simulating Save dialog for Experiment '{experiment_query or '17b'}'.")
        time.sleep(1.0)
        return True, None, None

    start_time = time.time()
    save_hwnd = None
    save_title = None

    log("[FOC48] Scanning for FOC48 'Save' dialog window...")
    while time.time() - start_time < timeout:
        h = user32.FindWindowW(None, "Save")
        if h and user32.IsWindowVisible(h):
            save_hwnd = h
            save_title = "Save"
            break

        candidates = find_windows_by_title("Save")
        if candidates:
            save_hwnd, save_title = candidates[0]
            break

        time.sleep(0.5)

    if not save_hwnd:
        log_err(f"[FOC48] Save dialog did not appear within {timeout}s.")
        return False, None, None

    foc_pid = get_window_pid(save_hwnd)
    main_hwnd = user32.GetWindow(save_hwnd, GW_OWNER) or user32.GetParent(save_hwnd)
    if not main_hwnd:
        main_cands = find_windows_by_title("Initialize Buffer") + find_windows_by_title("FOC48")
        if main_cands:
            main_hwnd = main_cands[0][0]

    log(f"[FOC48] Found '{save_title}' dialog (HWND: {save_hwnd}, PID: {foc_pid}, MainHWND: {main_hwnd}).")
    log(f"[FOC48] Waiting {init_delay:.1f}s for camera buffer and 48-well plots to finish initializing...")
    time.sleep(init_delay)

    user32.SetForegroundWindow(save_hwnd)
    time.sleep(0.5)

    rect = wintypes.RECT()
    user32.GetWindowRect(save_hwnd, ctypes.byref(rect))
    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top
    log(f"[FOC48] Save dialog rect: Left={rect.left}, Top={rect.top}, Width={win_w}, Height={win_h}")

    children = find_child_controls(save_hwnd)
    listboxes = [c for c in children if 'listbox' in c['class'].lower()]
    listboxes.sort(key=lambda c: c['rect'][0])
    log(f"[FOC48] Detected {len(children)} child controls ({len(listboxes)} ListBoxes).")

    xml_params = parse_xml_parameters()
    export_path = xml_params.get('exportPath')

    # --- STEP 1: SELECT EXPERIMENT (Left ListBox) ---
    if len(listboxes) >= 1:
        exp_lb = listboxes[0]
        exp_items = get_listbox_items(exp_lb['hwnd'])
        log(f"[FOC48] Experiment ListBox items: {exp_items if exp_items else 'Using folder scan fallback'}")
        target_exp_idx = resolve_experiment_index(experiment_query, exp_items, export_path=export_path, logger=logger)
        click_listbox_row(exp_lb['hwnd'], exp_lb['rect'], target_exp_idx, logger=logger)
    else:
        target_exp_idx = resolve_experiment_index(experiment_query, [], export_path=export_path, logger=logger)
        exp_x = rect.left + int(win_w * 0.18)
        exp_y = rect.top + int(win_h * 0.155) + (target_exp_idx * 16)
        log(f"[FOC48] Fallback Experiment click (Row {target_exp_idx}) at ({exp_x}, {exp_y}).")
        click_screen(exp_x, exp_y)

    # Wait for FOC48 to populate the Measurement ListBox for the selected Experiment
    time.sleep(1.2)

    # --- STEP 2: SELECT FIRST MEASUREMENT (Middle ListBox) ---
    if len(listboxes) >= 2:
        meas_lb = listboxes[1]
        meas_items = get_listbox_items(meas_lb['hwnd'])
        log(f"[FOC48] Measurement ListBox items: {meas_items[:5] if meas_items else 'Selecting top row (Row 0)'}")
        click_listbox_row(meas_lb['hwnd'], meas_lb['rect'], 0, logger=logger)
    else:
        meas_x = rect.left + int(win_w * 0.58)
        meas_y = rect.top + int(win_h * 0.155)
        log(f"[FOC48] Fallback Measurement click (Row 0) at ({meas_x}, {meas_y}).")
        click_screen(meas_x, meas_y)

    time.sleep(1.0)

    # --- STEP 3: ENSURE 'autoClose' IS CHECKED (Single action, NO double-toggle!) ---
    autoclose_ctrl = next((c for c in children if "autoclose" in c['text'].lower()), None)
    if autoclose_ctrl:
        chwnd = autoclose_ctrl['hwnd']
        crect = autoclose_ctrl['rect']
        cx = (crect[0] + crect[2]) // 2
        cy = (crect[1] + crect[3]) // 2
        chk_state = user32.SendMessageW(chwnd, BM_GETCHECK, 0, 0)
        if chk_state != BST_CHECKED:
            log(f"[FOC48] 'autoClose' is unchecked (state={chk_state}). Clicking once at ({cx}, {cy})...")
            click_screen(cx, cy)
            time.sleep(0.3)
            new_state = user32.SendMessageW(chwnd, BM_GETCHECK, 0, 0)
            if new_state != BST_CHECKED:
                log("[FOC48] Setting 'autoClose' via BM_CLICK backup...")
                user32.SendMessageW(chwnd, BM_CLICK, 0, 0)
        else:
            log("[FOC48] 'autoClose' is already checked.")
    else:
        fallback_cx = rect.left + int(win_w * 0.88)
        fallback_cy = rect.top + int(win_h * 0.86)
        log(f"[FOC48] 'autoClose' control not found by text. Clicking geometric position ({fallback_cx}, {fallback_cy}).")
        click_screen(fallback_cx, fallback_cy)

    time.sleep(0.6)

    # --- STEP 4: CLICK 'Save All' ONCE (Single physical click only!) ---
    saveall_ctrl = next((c for c in children if "save all" in c['text'].lower()), None)
    if saveall_ctrl:
        srect = saveall_ctrl['rect']
        sx = (srect[0] + srect[2]) // 2
        sy = (srect[1] + srect[3]) // 2
        log(f"[FOC48] Clicking 'Save All' button once at ({sx}, {sy})...")
        click_screen(sx, sy)
    else:
        fallback_sx = rect.left + int(win_w * 0.90)
        fallback_sy = rect.top + int(win_h * 0.75)
        log(f"[FOC48] 'Save All' control not found by text. Clicking geometric position ({fallback_sx}, {fallback_sy}).")
        click_screen(fallback_sx, fallback_sy)

    log("[FOC48] Experiment & Measurement selected, 'autoClose' checked, and 'Save All' triggered.")
    return True, foc_pid, main_hwnd


def wait_for_foc_completion(foc_pid=None, main_hwnd=None, duration=90, save_time=60, logger=None):
    """
    Waits for FOC48 to finish the full optical measurement (e.g. 90s duration),
    write the save data (e.g. 60s saveTime), turn off UV, and close the application.
    Tracks both the Windows Process ID (foc_pid) and FOC48 windows so it never exits early.
    """
    log = logger.info if logger else print
    log_warn = logger.warning if logger else print

    if not IS_WINDOWS or not user32:
        log(f"[FOC48] Non-Windows OS: Simulating {duration}s optical recording & {save_time}s save...")
        time.sleep(3.0)
        return True

    timeout = max(300.0, float(duration) + float(save_time) + 120.0)
    log(
        f"[FOC48] Recording in progress (XML duration={duration}s, saveTime={save_time}s). "
        f"Waiting up to {int(timeout)}s for FOC48 (PID={foc_pid}) to save, turn off UV, and close..."
    )

    start_time = time.time()
    last_log_time = start_time
    time.sleep(3.0)

    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time

        pid_alive = is_process_running(foc_pid) if foc_pid else False
        main_alive = bool(main_hwnd and user32.IsWindow(main_hwnd) and user32.IsWindowVisible(main_hwnd))
        save_windows = find_windows_by_title("Save")
        foc_windows = find_windows_by_title("Initialize Buffer") + find_windows_by_title("FOC48")

        if not pid_alive and not main_alive and not save_windows and not foc_windows:
            if elapsed < duration * 0.5:
                log_warn(
                    f"[FOC48] Warning: FOC48 closed after only {elapsed:.1f}s "
                    f"(expected ~{duration}s recording). Please verify Experiment/Measurement selection."
                )
            else:
                log(f"[FOC48] FOC48 finished recording, saved data, turned off UV, and closed after {elapsed:.1f}s.")
            time.sleep(1.5)
            return True

        if time.time() - last_log_time >= 15.0:
            log(f"[FOC48] Optical measurement/save in progress... ({int(elapsed)}s elapsed)")
            last_log_time = time.time()

        time.sleep(1.0)

    log_warn(f"[FOC48] Warning: Timeout ({int(timeout)}s) reached waiting for FOC48 to close. Resuming protocol.")
    return True


def execute_foc48_measurement(plate_name="", logger=None):
    """
    Main entry point for 'System: FOC48 Measurement'.
    1. Reads duration (90s) and saveTime (60s) from myrPlate.xml.
    2. Launches FOC48_autoOrgan.
    3. Selects Experiment (e.g. 17b for Plate 2 or 17a for Plate 1) and 1st Measurement.
    4. Checks autoClose and clicks Save All once.
    5. Waits for the full 90s measurement + 60s save + process exit before returning.
    """
    log = logger.info if logger else print
    log_err = logger.error if logger else print

    chosen_foc, chosen_xml = get_default_paths()
    xml_params = parse_xml_parameters(chosen_xml)
    duration = xml_params.get('duration', 90)
    save_time = xml_params.get('saveTime', 60)

    log(f"[FOC48] Target Executable / Shortcut: {chosen_foc}")
    log(
        f"[FOC48] Parameter XML: {chosen_xml} "
        f"(duration={duration}s, saveTime={save_time}s, Experiment='{plate_name or '17b (Default)'}')"
    )

    launched_proc = None
    if IS_WINDOWS:
        try:
            if chosen_foc.endswith('.lnk'):
                log(f"[FOC48] Launching desktop shortcut: {chosen_foc}")
                os.startfile(chosen_foc)
            else:
                cmd = [chosen_foc]
                if os.path.exists(chosen_xml):
                    cmd.append(chosen_xml)
                log(f"[FOC48] Launching subprocess: {cmd}")
                launched_proc = subprocess.Popen(cmd)
        except Exception as e:
            log_err(f"[FOC48] Error launching FOC48: {e}")
            fallback_lnk = r'C:\Users\labhub\Desktop\FOC48_autoOrgan.lnk'
            if os.path.exists(fallback_lnk):
                log(f"[FOC48] Trying fallback os.startfile('{fallback_lnk}')...")
                os.startfile(fallback_lnk)
    else:
        log("[FOC48] (Non-Windows environment) Mocking FOC48 launch.")

    # Step 2: Select Experiment, Select Measurement, Check autoClose, Click Save All
    ok, foc_pid, main_hwnd = handle_save_dialog(
        experiment_query=plate_name,
        logger=logger,
        timeout=45.0,
        init_delay=5.0
    )
    if not foc_pid and launched_proc:
        foc_pid = launched_proc.pid

    if not ok:
        log_err("[FOC48] Failed to interact with FOC48 Save dialog.")
        return False

    # Step 3: Wait for full recording (duration=90s) + save (saveTime=60s) + window/process close
    wait_for_foc_completion(
        foc_pid=foc_pid,
        main_hwnd=main_hwnd,
        duration=duration,
        save_time=save_time,
        logger=logger
    )

    log("[FOC48] Step completed successfully.")
    return True
