"""Writing the image a viewer hands back.

`save_screenshot` sends a command and then *polls for the file*, in every host,
because the browser answers on its own channel and not to the caller. So the
one thing that must never happen is a half-written file appearing at that path:
the poll would take it for a finished one. Writing beside it and renaming is
what makes the file exist only once it is complete.

Shared because two Python hosts do exactly this - the standalone's server and
build123d Studio's sidecar - and a race that has been thought about once should
not be thought about again per host.
"""

#
# Copyright 2026 Bernhard Walter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import base64
import shutil
import time


def save_png_data_url(data_url, output_path):
    """Write the image, under a temporary name first."""
    image_data = base64.b64decode(data_url.split(",")[1])
    suffix = "-temp" + hex(int(time.time() * 1e6))[2:]
    try:
        with open(output_path + suffix, "wb") as f:
            f.write(image_data)
        shutil.move(output_path + suffix, output_path)
        print(f"Wrote png file to {output_path}")
    except Exception as ex:  # noqa: BLE001
        print("Cannot save png file:", str(ex))
