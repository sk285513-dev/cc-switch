import sys
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.save('A:\\logs_v6\\system_screenshot.png')
    print("Screenshot saved via interactive scheduled task.")
except Exception as e:
    import traceback
    with open('A:\\logs_v6\\screenshot_error.txt', 'w') as f:
        traceback.print_exc(file=f)
