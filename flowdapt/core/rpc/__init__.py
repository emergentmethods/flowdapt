def register_rpc(rpc):
    from flowdapt.core.rpc.metrics import router as metrics_router
    from flowdapt.core.rpc.plugin import router as plugin_router
    from flowdapt.core.rpc.status import router as status_router

    rpc.add_rpc_router(status_router)
    rpc.add_rpc_router(plugin_router)
    rpc.add_rpc_router(metrics_router)
