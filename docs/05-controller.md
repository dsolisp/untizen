# Pair a PS5 DualSense natively

The tested U8000F has Bluetooth support (Samsung lists Bluetooth 5.3).
Quiet Home's **Settings → Controllers** card opens the television's native
Bluetooth device menu. No separate controller daemon is installed.

1. Disconnect the DualSense's USB cable and turn the controller off.
2. Hold **Create + PS** until the light bar flashes.
3. Open **Quiet Home → Settings → Controllers**.
4. Select **Wireless Controller** in the TV's device list and pair it.
5. Try D-pad navigation, Cross/Select and Circle/Back in Quiet Home.

Sony documents pairing mode and device support in
[DualSense Bluetooth pairing](https://www.playstation.com/en-us/support/hardware/pair-dualsense-controller-bluetooth/).
Samsung documents [TV gamepad support](https://developer.samsung.com/smarttv/accessory/gamepad.html).

Implementation: the launcher requests `org.tizen.menu` with
`menuitem=add-bluetooth-keyboard`, `launchoption=pressed`,
`__K_EX_FORCE_BOOST=enable` and the transparent splash hint. Despite the
internal “keyboard” name, this route reached the native Bluetooth list used
for the DualSense on the tested firmware.

Preserve Bluetooth and gamepad services during cleanup. The TV's input stack
delivers navigation events; support within streaming and cloud-gaming apps
depends on those apps. Successful pairing does not guarantee every button,
analog input, haptic or audio feature works everywhere.

Pairing the controller to the TV does **not** pass controller input through
HDMI to a PlayStation or other console. For console gameplay, pair it with
that console. Changing between hosts may require pairing again.
