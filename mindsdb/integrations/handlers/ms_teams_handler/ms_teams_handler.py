from mindsdb.integrations.handlers.utilities.api_utilities import MSGraphAPIClient
from mindsdb.integrations.handlers.utilities.auth_utilities import MSGraphAPIAuthManager

from mindsdb.integrations.handlers.ms_teams_handler.ms_teams_tables import ChannelsTable, ChannelMessagesTable
from mindsdb.integrations.libs.api_handler import APIChatHandler
from mindsdb.integrations.libs.response import (
    HandlerStatusResponse as StatusResponse,
)

from mindsdb.utilities import log
from mindsdb_sql import parse_sql

DEFAULT_SCOPES = [
    'https://graph.microsoft.com/User.Read',
    'https://graph.microsoft.com/Group.Read.All',
    'https://graph.microsoft.com/ChannelMessage.Send'
]

logger = log.getLogger(__name__)


class MSTeamsHandler(APIChatHandler):
    """
    The Microsoft Teams handler implementation.
    """

    name = 'teams'

    def __init__(self, name: str, **kwargs):
        """
        Initialize the handler.
        Args:
            name (str): name of particular handler instance
            **kwargs: arbitrary keyword arguments.
        """
        super().__init__(name)

        connection_data = kwargs.get("connection_data", {})
        self.connection_data = connection_data
        self.handler_storage = kwargs['handler_storage']
        self.kwargs = kwargs

        self.connection = None
        self.is_connected = False

        channels_data = ChannelsTable(self)
        self._register_table("channels", channels_data)

        channel_messages_data = ChannelMessagesTable(self)
        self._register_table("channel_messages", channel_messages_data)

    def connect(self):
        """
        Set up the connection required by the handler.
        Returns
        -------
        StatusResponse
            connection object
        """
        if self.is_connected is True:
            return self.connection

        ms_graph_api_auth_manager = MSGraphAPIAuthManager(
            handler_storage=self.handler_storage,
            scopes=self.connection_data.get('scopes', DEFAULT_SCOPES),
            client_id=self.connection_data["client_id"],
            client_secret=self.connection_data["client_secret"],
            tenant_id=self.connection_data["tenant_id"],
            code=self.connection_data.get('code')
        )

        access_token = ms_graph_api_auth_manager.get_access_token()

        self.connection = MSGraphAPIClient(access_token)

        self.is_connected = True

        return self.connection

    def check_connection(self) -> StatusResponse:
        """
        Check connection to the handler.
        Returns:
            HandlerStatusResponse
        """

        response = StatusResponse(False)

        try:
            connection = self.connect()
            connection.get_user_profile()
            response.success = True
            response.copy_storage = True
        except Exception as e:
            logger.error(f'Error connecting to Microsoft Teams: {e}!')
            response.error_message = str(e)

        self.is_connected = response.success

        return response

    def native_query(self, query: str) -> StatusResponse:
        """Receive and process a raw query.
        Parameters
        ----------
        query : str
            query in a native format
        Returns
        -------
        StatusResponse
            Request status
        """
        ast = parse_sql(query, dialect="mindsdb")
        return self.query(ast)
    
    def get_chat_config(self):
        params = {
            'polling': {

            },
            'chat_table': {

            }
        }
        return params
    
    def get_my_user_name(self):
        connection = self.connect()
        user_profile = connection.get_user_profile()
        return user_profile['displayName']