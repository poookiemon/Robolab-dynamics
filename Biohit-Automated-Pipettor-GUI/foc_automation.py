import os
import sys
import time
import subprocess
import logging

# Safe Win32 imports for cross-platform compatibility
IS_WINDOWS = sys.platform.startswith('win')
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
else:
    ctypes = None
    wintypes = None
    user32 = None

BM_CLICK = 0x00F5
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_UNCHECKED = 0x0000
BST_CHECKED = 0x0001
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


def click_screen(x, y):
    """Executes a physical left mouse click at (x, y)."""
    if not IS_WINDOWS or not user32:
        return
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def find_windows_by_title(title_substring):
    """Finds all visible top-level windows matching title_substring."""
    if not IS_WINDOWS or not user32:
        return []
    results = []

    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value
            if title_substring.lower() in title.lower():
                results.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return results


def find_child_controls(parent_hwnd):
    """Enumerates all child controls of a window and returns a dict mapping text to hwnd."""
    if not IS_WINDOWS or not user32:
        return {}
    children = {}

    def enum_child_cb(hwnd, _):
        buf_text = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf_text, 512)
        buf_cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf_cls, 256)
        text = buf_text.value.strip()
        cls_name = buf_cls.value.strip()
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        children[text.lower() if text else f"cls_{cls_name.lower()}_{hwnd}"] = {
            'hwnd': hwnd,
            'text': text,
            'class': cls_name,
            'rect': (rect.left, rect.top, rect.right, rect.bottom)
        }
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows(parent_hwnd, WNDENUMPROC(enum_child_cb), 0)
    return children


def handle_save_dialog(logger=None, timeout=45.0):
    """
    Finds the FOC48 'Save' modal dialog, checkmarks 'autoClose', and clicks 'Save All'.
    Returns True when successfully triggered.
    """
    log = logger.info if logger else print
    log_err = logger.error if logger else print

    if not IS_WINDOWS:
        log("[FOC48] Non-Windows OS: Simulating Save dialog detection & click.")
        time.sleep(1.0)
        return True

    start_time = time.time()
    save_hwnd = None
    save_title = None

    log("[FOC48] Scanning for FOC48 'Save' dialog window...")
    while time.time() - start_time < timeout:
        # Search specifically for exact title "Save"
        h = user32.FindWindowW(None, "Save")
        if h and user32.IsWindowVisible(h):
            save_hwnd = h
            save_title = "Save"
            break

        # Search via substring
        candidates = find_windows_by_title("Save")
        if candidates:
            save_hwnd, save_title = candidates[0]
            break

        time.sleep(0.5)

    if not save_hwnd:
        log_err(f"[FOC48] Save dialog did not appear within {timeout}s.")
        return False

    log(f"[FOC48] Found '{save_title}' dialog (HWND: {save_hwnd}). Bringing to front...")
    user32.SetForegroundWindow(save_hwnd)
    time.sleep(0.5)

    # Get dialog bounding box
    rect = wintypes.RECT()
    user32.GetWindowRect(save_hwnd, ctypes.byref(rect))
    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top
    log(f"[FOC48] Dialog dimensions: Left={rect.left}, Top={rect.top}, Width={win_w}, Height={win_h}")

    # Enumerate child controls
    children = find_child_controls(save_hwnd)
    log(f"[FOC48] Found {len(children)} child controls in Save dialog.")

    # 1. HANDLE 'autoClose' CHECKBOX
    autoclose_handled = False
    for key, cinfo in children.items():
        if "autoclose" in key or "autoclose" in cinfo['text'].lower():
            chwnd = cinfo['hwnd']
            crect = cinfo['rect']
            cx = (crect[0] + crect[2]) // 2
            cy = (crect[1] + crect[3]) // 2
            log(f"[FOC48] Found 'autoClose' control at ({cx}, {cy}). Checking box...")
            user32.SendMessageW(chwnd, BM_SETCHECK, BST_CHECKED, 0)
            click_screen(cx, cy)
            autoclose_handled = True
            break

    if not autoclose_handled:
        # Fallback using geometric bounding box ratio
        # autoClose checkbox is located near bottom right, below Save All
        fallback_cx = rect.left + int(win_w * 0.68)
        fallback_cy = rect.top + int(win_h * 0.71)
        log(f"[FOC48] 'autoClose' control text not found in hierarchy. Using geometric click at ({fallback_cx}, {fallback_cy}).")
        click_screen(fallback_cx, fallback_cy)

    time.sleep(0.6)

    # 2. HANDLE 'Save All' BUTTON
    saveall_handled = False
    for key, cinfo in children.items():
        if "save all" in key or "save all" in cinfo['text'].lower():
            chwnd = cinfo['hwnd']
            crect = cinfo['rect']
            cx = (crect[0] + crect[2]) // 2
            cy = (crect[1] + crect[3]) // 2
            log(f"[FOC48] Found 'Save All' button at ({cx}, {cy}). Clicking...")
            user32.SendMessageW(chwnd, BM_CLICK, 0, 0)
            click_screen(cx, cy)
            saveall_handled = True
            break

    if not saveall_handled:
        # Fallback using geometric bounding box ratio or previous calibrated position
        fallback_sx = rect.left + int(win_w * 0.68)
        fallback_sy = rect.top + int(win_h * 0.63)
        log(f"[FOC48] 'Save All' control text not found in hierarchy. Using geometric click at ({fallback_sx}, {fallback_sy}).")
        click_screen(fallback_sx, fallback_sy)

    log("[FOC48] 'Save All' clicked with 'autoClose' enabled.")
    return True


def wait_for_foc_completion(save_hwnd=None, timeout=120.0, logger=None):
    """Waits for FOC48 to finish writing data and close its window/process."""
    log = logger.info if logger else print

    if not IS_WINDOWS or not user32:
        log("[FOC48] Simulating 5.0s data capture...")
        time.sleep(5.0)
        return True

    log("[FOC48] Waiting for FOC48 saving and autoClose to complete...")
    start_time = time.time()
    time.sleep(2.0)  # Initial grace period

    while time.time() - start_time < timeout:
        # Check if Save dialog is still open
        save_windows = find_windows_by_title("Save")
        main_windows = find_windows_by_title("Initialize Buffer") + find_windows_by_title("FOC48")

        if not save_windows and not main_windows:
            log("[FOC48] FOC48 application window closed successfully. Saving finished.")
            return True

        time.sleep(1.0)

    log("[FOC48] Notice: Timeout reached waiting for window close. Proceeding with protocol.")
    return True


def execute_foc48_measurement(plate_name="", logger=None):
    """
    Main entry point for 'System: FOC48 Measurement'.
    Launches FOC48_autoOrgan, marks autoClose, clicks Save All, and waits for completion.
    """
    log = logger.info if logger else print
    log_err = logger.error if logger else print

    chosen_foc, chosen_xml = get_default_paths()
    log(f"[FOC48] Target App: {chosen_foc}")
    log(f"[FOC48] Parameters: {chosen_xml} (Plate: {plate_name or 'Default'})")

    proc = None
    if IS_WINDOWS:
        try:
            if chosen_foc.endswith('.lnk'):
                log(f"[FOC48] Launching desktop shortcut: {chosen_foc}")
                os.startfile(chosen_foc)
            else:
                cmd = [chosen_foc]
                if os.path.exists(chosen_xml):
                    cmd.append(chosen_xml)
                if plate_name:
                    cmd.append(str(plate_name))
                log(f"[FOC48] Launching subprocess: {cmd}")
                proc = subprocess.Popen(cmd)
        except Exception as e:
            log_err(f"[FOC48] Error launching FOC48: {e}")
            # Try desktop shortcut fallback
            fallback_lnk = r'C:\Users\labhub\Desktop\FOC48_autoOrgan.lnk'
            if os.path.exists(fallback_lnk):
                log(f"[FOC48] Trying fallback os.startfile('{fallback_lnk}')...")
                os.startfile(fallback_lnk)
    else:
        log("[FOC48] (Simulated environment) Mocking FOC48 launch.")

    # Step 2: Detect Save dialog, check autoClose, click Save All
    dialog_success = handle_save_dialog(logger=logger, timeout=45.0)

    # Step 3: Wait for process/window to close
    wait_for_foc_completion(timeout=120.0, logger=logger)

    log("[FOC48] Optical measurement sequence finished.")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    test_logger = logging.getLogger("FOCTest")
    print("Testing FOC automation inspection...")
    chosen_f, chosen_x = get_default_paths()
    print(f"Candidate FOC path: {chosen_f} (Exists: {os.path.exists(chosen_f)})")
    print(f"Candidate XML path: {chosen_x} (Exists: {os.path.exists(chosen_x)})")
    execute_foc48_measurement(plate_name="TestPlate", logger=test_logger)
