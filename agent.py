import pyautogui
import time
import pyperclip

def reply_to_whatsapp(contact_name, message):
    pyautogui.hotkey('ctrl', 'alt', 'w')
    time.sleep(2)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)
    pyperclip.copy(contact_name)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('esc')
    time.sleep(1)
    pyperclip.copy(message)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)
    pyautogui.press('enter')

reply_to_whatsapp("John", "Hello, this is an automated reply.")