# Enabling the web frontend of the Tibber Pulse Bridge [*Required*]

To enable the web frontend permanently, one local variable needs to be set in the web frontend. But to get into the web frontend for the first time, you need to start the Tibber Pulse Bridge in AccessPoint mode. This can be done by the following steps:

## 1. Start AP-Mode

> [!TIP]
> While you have unplugged the bridge you might like to use the opportunity to get the password from the bottom of the plug - e.g. by taking a photo (see also step 2: 'Connect to the Pulse Bridge WiFi AccessPoint').

* Unplug the Tibber bridge.
* After three seconds, plug the Tibber bridge.
* After three seconds, unplug the Tibber bridge.
* After three seconds, plug the Tibber bridge.

The LED on the Tibber bridge should now light up green and not light blue anymore.

If this is not the case, then try this alternative:

* Unplug the Tibber bridge.
* Plug the Tibber bridge
* When the bridge light in __yellow__ then unplug the bridge again
* Wait for a short while and plug in the bridge again after few seconds

NOW the LED on the Tibber bridge should now light up green and not light blue anymore.

## 2. Connect to the Pulse Bridge WiFi AccessPoint

Now use any device (laptop, tablet, phone) to connect to the `Tibber Bridge` WiFi network. The password for the WiFi is the nine characters printed on the Tibber bridge - it's important to include the dash. The password should have the pattern like this example one: `AD56-54BA`.

![img|160x90](../images/bridge-pwd-location.png)

## 3. Set `webserver_force_enable` to `true` in the web frontend

After you are connected to the WiFi that have been created by the Pulse Bridge with your laptop/phone, use a web browser on that device to connect to <http://10.133.70.1/>. You will be prompted for a user and a password (BasicAuth).

The username is `admin` and the password is again the nine characters printed on the Tibber bridge.

Depending on the hardware revision and firmware, there are two alternatives to archive this goal. Please select the procedure that fits your situation.

### Via CONSOLE-Tab

With a recent firmware release the `webserver_force_enable` flag (39) does __not appear__ any longer in the param list. So the console tab is the way to go!

1. Go to <http://10.133.70.1/console/>
2. type `param_get 39` (just to ensure, that the system still know the `webserver_force_enable` parameter) - you can also try to type `param_get webserver_force_enable` [and press the `send` button afterwards] - this should give you some output like this:
   ```
   tibber-bridge> param_get 39
   esp32> param_get 39
   webserver_force_enable (39):
   false
   Command 'param_get 39' executed successfully
   ```
3. So if `39` (= `webserver_force_enable`) is still present, then and __only then__ you can continue!

4. type `param_set 39 TRUE` (the upper case of TRUE is important here) [and press the `send` button afterward]
5. type `param_store` [and press the `send` button afterward]
6. for confirmation, you can type again `param_get 39` [and press the `send` button afterward]

### Via PARAMS-Tab [previously the default procedure]

1. Go to <http://10.133.70.1/params/>
2. Find the variable `webserver_force_enable` in the list
3. Set the value to `true` (lower case)
4. Press *"Store params to flash"* on the bottom of the page.

__Please do not modify any other values in the params list!__

## 4. Bring your Pulse & Bridge back to normal operation

Unplug the Tibber bridge, wait __ten seconds__ and plug it back again. Now it should connect back to your previously configured WiFi and should work as before (submit the data to Tibber) - the LED should light up light blue again.

## 5. Final testing [do not continue if you did not complete this final step]

### Part I: Access the web frontend

After you have successfully reset the Tibber bridge (AP mode is OFF and you are back in normal operation mode). Since you have set the `webserver_force_enable` to `true` the web frontend should now be still accessible via the following URL:
<http://tibber-host/> or <http://tibber-bridge/>.

If the hostname 'tibber-host' (or 'tibber-bridge') is not going to work for you in your LAN, you might like to check the IP-Address of your Tibber Pulse Bridge in your Router. __The IP *is not* the `10.133.70.1` any longer!__

It is recommended to configure your router so that the Pulse Bridge always gets the same IP address (DHCP reservation). Accessing the device via IP (instead of the host name) also saves DNS lookups.

When you open the web frontend of the bridge, you always have to provide the user `admin` and the password.

![img|160x90](../images/web-frontend.png)

Now (when the frontend works for you) almost everything is prepared... Just one more thing to check:

### Part II: Ensure that there is at least one node paired with the bridge

Some users try to use this integration _without having paired_ the Tibber Pulse reading head (the part is mounted at your power meter) with the Tibber Pulse Bridge. For sure, this is not going to work! The pairing procedure is part of the regular Tibber Pulse setup process with your Tibber app - so probably you have done this already - but just in case:

Please double-check by opening the `http://[YOUR-IP]/pulse/` (old fw `http://[YOUR-IP]/nodes/`) section (you can select from the menu the 'Pulse' (old fw 'NODES' entry)) and ensure, that there is at least one node listed - which means that the bridge is connected with the reading-head-unit.

Here you can also check, if the node is listed with the (expected) default NodeId value `1`. If you have a different NodeId, then you need to adjust the expert setting `Node Number (expert setting)` when configure this integration.

### Part III: Check 'Last seen' & 'Last data' [update frequency]

1. Go to `http://[YOUR-IP]/pulse/` (old fw `http://[YOUR-IP]/nodes/`) (just like in part II)
2. Take a look at the value `Last seen`/`Last data`

   This last data value is the last time (in seconds) the bridge has received a data update from the reading head. This value should not be higher than 2.5-5 seconds.

   If your `Last seen`/`Last data` is frequently recently greater than this, then this integration can't work in a reliable way.

   __Rotate the reading head few degrees anti-clock wise in order to check, if the update frequency will be better (smaller).__

   ![img|20x20](../images/rotate_head.png)

   A community report in the original project ([upstream issue marq24/ha-tibber-pulse-local#6](https://github.com/marq24/ha-tibber-pulse-local/issues/6#issuecomment-1791117188)) shows what a difference even a few degrees can make.


### Finally, you are done!

When part I, II & III are completed/confirmed, __then__ you can install and use the **Pulse Bridge for Tibber** integration ([installation guide](installation.md)).
