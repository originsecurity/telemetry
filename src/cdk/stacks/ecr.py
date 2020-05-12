from aws_cdk import (core, aws_ecr as ecr)

class ECRStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)


        # create ECR repository
        self.ecr_repository = ecr.Repository(
            scope=self,
            id="ecr"
        )

        repo_name_output = core.CfnOutput(
            scope=self,
            id="ecr-repo-name-out",
            value=self.ecr_repository.repository_name,
            export_name=f"{id}-ecr-repo-name"
        )
