def register_rpc(rpc):
    from flowdapt.triggers.rpc.triggers import router as trigger_router

    rpc.add_rpc_router(trigger_router)
