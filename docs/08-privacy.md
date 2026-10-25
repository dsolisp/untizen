# What the privacy cleanup means

We disabled selected advertising, content-recognition, analytics and optional
voice/context components. “Disabled” means recorded registry flags,
service-stop conditions and process checks—not proof that every related
binary was deleted or every possible data flow was blocked.

## Content recognition and screen sampling

Automatic Content Recognition (ACR) can sample displayed content, derive a
fingerprint and compare it with a reference library to identify programs or
ads. It is more accurate to describe this as **screen-content fingerprinting**
than to assert that readable screenshots of everything on this TV were
uploaded. Samsung describes ACR under its optional Viewing Information
Services in [its ACR explanation](https://www.samsung.com/us/support/answer/ANS10010616/).

A [2024 academic measurement study](https://arxiv.org/html/2409.06203v1)
found ACR network activity on the Samsung/LG models it tested even when they
were used as HDMI displays. Opting out stopped observed ACR traffic. In those
experiments, Netflix and YouTube playback did not produce the same ACR traffic.
The paper concerns other devices and firmware, not a direct audit of this
2025 U8000F. It does not establish that arbitrary laptop text was uploaded
as readable screenshots.

Relevant disabled app IDs here included `com.samsung.tv.acr`,
`com.samsung.tv.canalysis-service` and
`com.samsung.tv.contents-recognition-dbmgr`. Additional recognition masking
was runtime-only. These observations support a targeted reduction of known
components, not a quantified reduction in tracking traffic.

## Advertising and usage profiles

The cleanup targeted Samsung analytics, PISA/ad-agent, targeted-ad and
promotion records. Samsung's [US privacy policy](https://www.samsung.com/us/account/privacy-policy/)
describes collection of device identifiers, usage information and, depending
on the feature and choices, voice information and information from other
sources. Such data can support personalized services and advertising.

That policy is broader than one TV's observed behavior. We did not decrypt
this TV's traffic, inspect a server-side profile or establish which exact
records had been transmitted. Some differently packaged ad or smart-service
components remained. Streaming apps retain their own privacy practices.

## Voice and context features

The owner did not want Bixby/Alexa wake-word services, voice UI, utterance
suggestions or context-aware helpers. Their registry records, selected
service conditions and enablement preferences were changed accordingly.

A wake-word detector is not by itself evidence of continuous room audio
being uploaded for advertising. Nothing in this investigation established
that claim. Likewise, package names such as `content-grab-service` suggest
a capture-related role but do not alone prove what leaves the TV.

## Useful boundaries

- Use Samsung's consent/privacy controls too; a root modification is not
  required to exercise documented ACR opt-out choices.
- Keep optional-feature removal separate from malware claims. Health,
  ambience and device-integration features may be useful to another owner.
- A firmware/catalog update can restore settings or introduce new paths.
- HDMI-only use does not automatically mean zero tracking; disabling a
  launcher advertisement also does not establish zero tracking.
- No camera spying, perpetual room recording or arbitrary screenshot
  exfiltration was demonstrated on this device.

If stronger assurances are needed, perform a separate, consented network
measurement with explicit before/after tests and document its blind spots.
Do not publish private viewing history, identifiers or account traffic.
