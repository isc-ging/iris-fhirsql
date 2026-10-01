import json
from typing import List, Optional
try:
    import iris
except ImportError:
    # Optional dependency: only FHIR server discovery (DB API) needs it.
    iris = None
from iris_fhirsql.resources.base import BaseResource
from iris_fhirsql.models import Repository, FHIRServer
from iris_fhirsql.exceptions import ValidationError

class RepositoryResource(BaseResource):
    def list(self) -> List[Repository]:
        data = self._make_request("GET", "/fhirrepository/")
        return [Repository.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, repository_id: str) -> Repository:
        data = self._make_request("GET", "/fhirrepository", params={"ID": repository_id})
        return Repository.from_dict(data)

    def create(self, name: str, host: str, fhir_url: str,
               port: Optional[int] = None,
               internal_port: Optional[int] = None,
               credentials_name: Optional[str] = None,
               ssl_config: Optional[str] = None) -> Repository:
        """
        Create a FHIR repository configuration.

        For Docker containers with port mapping, use internal_port for the container's
        internal port while the client uses the mapped external port.

        Args:
            name: Display name for this repository
            host: Hostname (e.g., "localhost")
            fhir_url: FHIR endpoint path (e.g., "/fhir/r4")
            port: Port to use (defaults to client's port if not specified)
            internal_port: For containers - the port FHIR server runs on internally.
                          If specified, this is used instead of port.
            credentials_name: Credential system_name (not id!) to use for authentication
            ssl_config: Optional SSL configuration name

        Examples:
            # Simple case (no containers) - uses client's port automatically
            repo = client.repositories.create(
                name="My FHIR Server",
                host="localhost",
                fhir_url="/fhir/r4",
                credentials_name="MyCredentials"
            )

            # Docker container with port mapping (external 32783 -> internal 52773)
            # Client connects to 32783, but repo config needs internal port 52773
            repo = client.repositories.create(
                name="Containerized FHIR",
                host="localhost",
                fhir_url="/fhir/r4",
                internal_port=52773,  # Port inside container
                credentials_name="MyCredentials"
            )
        """
        if not all([name, host, fhir_url]):
            raise ValidationError("name, host, and fhir_url required")

        # Determine which port to use
        # Priority: internal_port > port > client's port
        if internal_port is not None:
            final_port = internal_port
        elif port is not None:
            final_port = port
        else:
            # Extract port from client's base_url
            # base_url format: http://hostname:port/csp/fhirsql/api/ui
            import re
            match = re.search(r':(\d+)/', self.client.base_url)
            if match:
                final_port = int(match.group(1))
            else:
                raise ValidationError("Could not determine port - please specify port or internal_port")

        if not isinstance(final_port, int) or final_port <= 0 or final_port > 65535:
            raise ValidationError("port must be an integer between 1 and 65535")

        repo = Repository(
            name=name,
            hostname=host,
            port=str(final_port),
            repository_url=fhir_url,
            credentials_id=credentials_name,  # API expects system_name, not id
            ssl_config=ssl_config
        )
        data = self._make_request("POST", "/fhirrepository", json=repo.to_dict())

        # API returns a list of all repositories, find the one we just created by name
        if isinstance(data, list):
            for item in data:
                if item.get("name") == name:
                    return Repository.from_dict(item)
            # If not found, return the last one (likely the newly created one)
            if data:
                return Repository.from_dict(data[-1])

        return Repository.from_dict(data)

    def update(self, repository: Repository) -> Repository:
        if not repository.id:
            raise ValidationError("Repository ID required for update")
        data = self._make_request("PUT", "/fhirrepository", json=repository.to_dict())
        return Repository.from_dict(data)

    def delete(self, repository_id: str) -> bool:
        self._make_request("DELETE", "/fhirrepository", params={"ID": repository_id})
        return True

    def _connect(self, namespace: str):
        username, password = self.client.session.auth
        return iris.connect(self.client.hostname, self.client.superserver_port,
                            namespace, username, password)

    def find_fhir_servers(self, namespace: Optional[str] = None,
                          include_disabled: bool = False) -> List[FHIRServer]:
        """
        Find FHIR server endpoints on the IRIS instance via the DB API.

        Connects over the client's superserver_port (required) and queries
        HS_FHIRServer.RepoInstance. The instance's internal web server port is
        read from ^%SYS("WebServer","Port"). Decommissioned endpoints are always
        excluded. An empty list means no (enabled) FHIR servers were found.

        Args:
            namespace: Namespace to search. If omitted, every available namespace
                       containing HS_FHIRServer.RepoInstance is searched.
            include_disabled: Also return endpoints with isEnabled = 0

        Example:
            client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)
            servers = client.repositories.find_fhir_servers()
        """
        if iris is None:
            raise ImportError(
                "intersystems-irispython is required for FHIR server discovery: "
                "pip install intersystems-irispython"
            )
        if self.client.superserver_port is None:
            raise ValidationError(
                "superserver_port not defined: pass superserver_port to FHIRSQLClient "
                "to use FHIR server discovery (e.g., 1972, or the mapped port for a container)"
            )
        conn = self._connect(namespace or "%SYS")
        try:
            web_port = int(iris.createIRIS(conn).get("^%SYS", "WebServer", "Port"))
            if namespace is not None:
                return self._query_fhir_servers(conn, namespace, web_port, include_disabled)
            cursor = conn.cursor()
            cursor.execute("SELECT Nsp, Status FROM %SYS.Namespace_List()")
            namespaces = cursor.fetchall()
        finally:
            conn.close()

        servers = []
        for i, (ns, status) in enumerate(namespaces, start=1):
            if status != "1":
                print(f"[{i}/{len(namespaces)}] Skipping {ns}: namespace unavailable (status {status})")
                continue
            ns_conn = self._connect(ns)
            try:
                cursor = ns_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                               "WHERE TABLE_SCHEMA = 'HS_FHIRServer' AND TABLE_NAME = 'RepoInstance'")
                if cursor.fetchone()[0] == 0:
                    print(f"[{i}/{len(namespaces)}] {ns}: no FHIR server table")
                    continue
                found = self._query_fhir_servers(ns_conn, ns, web_port, include_disabled)
            finally:
                ns_conn.close()
            print(f"[{i}/{len(namespaces)}] {ns}: {len(found)} FHIR server(s)")
            servers.extend(found)
        return servers

    def _query_fhir_servers(self, conn, namespace: str, web_port: int,
                            include_disabled: bool) -> List[FHIRServer]:
        sql = ("SELECT name, cspUrl, isEnabled, serviceConfigData "
               "FROM HS_FHIRServer.RepoInstance WHERE IsDecommissioned = 0")
        if not include_disabled:
            sql += " AND isEnabled = 1"
        cursor = conn.cursor()
        cursor.execute(sql)
        return [
            FHIRServer(
                namespace=namespace,
                csp_url=csp_url,
                fhir_version=json.loads(service_config)["fhir_version"],
                web_port=web_port,
                is_enabled=bool(is_enabled),
                name=name,
            )
            for name, csp_url, is_enabled, service_config in cursor.fetchall()
        ]

    def create_from_fhir_server(self, server: FHIRServer,
                                credentials_name: Optional[str] = None,
                                name: Optional[str] = None,
                                host: str = "localhost",
                                ssl_config: Optional[str] = None) -> Repository:
        """
        Register a discovered FHIR server as an FSB repository.

        Uses the server's internal web port, so this works for containers with
        port mapping. host is the hostname as seen by the FSB instance
        ("localhost" when the FHIR server runs on the same IRIS instance).

        Args:
            server: FHIRServer returned by find_fhir_servers()
            credentials_name: Credential system_name to use for authentication
            name: Repository name (defaults to server.name, or "<namespace><cspUrl>"
                  since RepoInstance.name is usually empty)
            host: Hostname the FSB uses to reach the FHIR server
            ssl_config: Optional SSL configuration name
        """
        return self.create(
            name=name or server.name or f"{server.namespace}{server.csp_url}",
            host=host,
            fhir_url=server.csp_url,
            internal_port=server.web_port,
            credentials_name=credentials_name,
            ssl_config=ssl_config,
        )

    def add_fhir_servers(self, servers: List[FHIRServer],
                         credentials_name: Optional[str] = None,
                         host: str = "localhost") -> List[Repository]:
        """
        Register each discovered FHIR server as an FSB repository, skipping any
        already registered with the same host, port and URL.

        Example:
            servers = client.repositories.find_fhir_servers()
            repos = client.repositories.add_fhir_servers(servers, credentials_name="SuperUser")
        """
        existing = {(r.hostname, str(r.port), r.repository_url) for r in self.list()}
        created = []
        for i, server in enumerate(servers, start=1):
            key = (host, str(server.web_port), server.csp_url)
            if key in existing:
                print(f"[{i}/{len(servers)}] Skipping {server.csp_url}: already registered")
                continue
            print(f"[{i}/{len(servers)}] Adding {host}:{server.web_port}{server.csp_url}")
            created.append(self.create_from_fhir_server(server, credentials_name, host=host))
        return created
