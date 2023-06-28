from jira import JIRA
import pandas as pd
import requests as rq
import os

TRELLO_KEY = os.environ.get("TRELLO_API_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_API_TOKEN")
TRELLO_BOARD_ID = os.environ.get("TRELLO_BOARD_ID")
TRELLO_API_BASE_URL = "https://api.trello.com"
JIRA_PROJECT_KEY = os.environ.get(
    "JIRA_PROJECT_KEY"
)  # Prefix key in ticket number e.g. ABC-1234. Put ABC here
JIRA_QUERY = os.environ.get(
    "JIRA_QUERY",
    f"project = {JIRA_PROJECT_KEY} AND (fixVersion in unreleasedVersions() OR updated > -1w) ORDER BY updated ASC, priority DESC",
)


class Jira2Trello:
    def __init__(self):
        self.jira = JIRA(
            basic_auth=(
                os.environ.get("JIRA_LOGIN_EMAIL"),
                os.environ.get("JIRA_API_TOKEN"),
            ),
            server=os.environ.get("JIRA_SERVER")
            # server link i.e. 'https://something.atlassian.net'
        )
        self.lists = {}
        self.get_lists_on_board()

    def create_card_in_list(
        self, ticket_number, ticket_summary, ticket_status, ticket_description
    ):
        if ticket_status not in self.lists:
            self.create_list_on_board(ticket_status)
            self.get_lists_on_board()
        li = self.lists[ticket_status]
        rq.post(
            f"{TRELLO_API_BASE_URL}/1/cards?idList={li}&key={TRELLO_KEY}&token={TRELLO_TOKEN}",
            json={
                "name": ticket_number + " " + ticket_summary,
                "desc": ticket_description,
            },
        )

    def create_list_on_board(self, list_name):
        resp = rq.post(
            f"{TRELLO_API_BASE_URL}/1/lists?idBoard={TRELLO_BOARD_ID}&key={TRELLO_KEY}&token={TRELLO_TOKEN}",
            json={"name": list_name},
        )

    def get_lists_on_board(self):
        lists_resp = rq.get(
            f"{TRELLO_API_BASE_URL}/1/boards/{TRELLO_BOARD_ID}/lists?key={TRELLO_KEY}&token={TRELLO_TOKEN}"
        )
        self.lists = {}
        for li in lists_resp.json():
            self.lists[li["name"]] = li["id"]

    def archive_all_cards_in_all_lists(self):
        for name, id in self.lists.items():
            rq.post(
                f"{TRELLO_API_BASE_URL}/1/lists/{id}/archiveAllCards?key={TRELLO_KEY}&token={TRELLO_TOKEN}"
            )

    def export_jira_issues(self):
        issues = self.jira.search_issues(
            JIRA_QUERY, maxResults=False, fields="key,status,summary,description"
        )
        return pd.DataFrame(self.jira_issue_to_dict(issue) for issue in issues)

    def jira_issue_to_dict(self, issue):
        return {
            "Issue key": issue.key,
            "Summary": issue.fields.summary,
            "Status": issue.fields.status.name,
            "Description": issue.fields.description,
        }

    def import_data(self):
        print("Exporting jira issues from JIRA")
        df = self.export_jira_issues()
        print("Exported issues")
        print("Archiving all cards on Trello board")
        self.archive_all_cards_in_all_lists()
        print("Creating cards on Trello board")
        for row in df.iterrows():
            self.create_card_in_list(
                row[1].get("Issue key"),
                row[1].get("Summary"),
                row[1].get("Status"),
                row[1].get("Description"),
            )
        print("Done")


if __name__ == "__main__":
    Jira2Trello().import_data()
