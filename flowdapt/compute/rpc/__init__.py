def register_rpc(rpc):
    from flowdapt.compute.rpc.config import router as config_router
    from flowdapt.compute.rpc.workflow import router as workflow_router

    rpc.add_rpc_router(workflow_router)
    rpc.add_rpc_router(config_router)
