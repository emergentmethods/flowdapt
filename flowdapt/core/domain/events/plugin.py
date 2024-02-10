from flowdapt.lib.rpc.eventbus.event import Event


class PluginsReloadEvent(Event):
    channel: str = "internal"
    type: str = "com.event.plugin.plugins_reload"
    data: None = None
