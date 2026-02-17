"""All GraphQL query strings as constants."""

REPO_OVERVIEW = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    owner { login }
    description
    stargazerCount
    forkCount
    isArchived
    defaultBranchRef { name }
    createdAt
    pushedAt
    primaryLanguage { name }
    licenseInfo { spdxId }
    openIssues: issues(states: OPEN) { totalCount }
    closedIssues: issues(states: CLOSED) { totalCount }
    openPRs: pullRequests(states: OPEN) { totalCount }
    mergedPRs: pullRequests(states: MERGED) { totalCount }
    closedPRs: pullRequests(states: CLOSED) { totalCount }
    releases(first: 5, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { tagName createdAt }
    }
  }
}
"""

MERGED_PRS_PAGE = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          author { login }
          mergedBy { login }
          createdAt
          mergedAt
          closedAt
          labels(first: 10) { nodes { name } }
          additions
          deletions
          changedFiles
          reviews(first: 1) { totalCount }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

CLOSED_PRS_PAGE = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: CLOSED, first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          author { login }
          createdAt
          closedAt
          labels(first: 10) { nodes { name } }
          additions
          deletions
          changedFiles
          reviews(first: 1) { totalCount }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

OPEN_PRS_PAGE = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          author { login }
          createdAt
          labels(first: 10) { nodes { name } }
          additions
          deletions
          changedFiles
          reviews(first: 1) { totalCount }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

USER_OPEN_PRS = """
query($searchQuery: String!) {
  search(query: $searchQuery, type: ISSUE, first: 20) {
    nodes {
      ... on PullRequest {
        number
        title
        author { login }
        createdAt
        labels(first: 10) { nodes { name } }
        additions
        deletions
        changedFiles
        reviews(first: 5) {
          nodes { state author { login } }
          totalCount
        }
        repository { nameWithOwner }
      }
    }
  }
}
"""

COMMIT_HISTORY = """
query($owner: String!, $name: String!, $since: GitTimestamp!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(since: $since, first: 100) {
            totalCount
            edges {
              node {
                committedDate
                author { user { login } }
                additions
                deletions
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
  }
}
"""

MERGED_PRS_WITH_REVIEWS = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          author { login }
          mergedBy { login }
          createdAt
          mergedAt
          labels(first: 10) { nodes { name } }
          additions
          deletions
          changedFiles
          reviews(first: 10) {
            nodes {
              author { login }
              state
              submittedAt
            }
            totalCount
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

OPEN_PRS_WITH_REVIEWS = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          author { login }
          createdAt
          labels(first: 10) { nodes { name } }
          additions
          deletions
          changedFiles
          reviews(first: 10) {
            nodes {
              author { login }
              state
              submittedAt
            }
            totalCount
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

ISSUE_TIMELINE = """
query($owner: String!, $name: String!, $first: Int!, $cursor: String!) {
  repository(owner: $owner, name: $name) {
    issues(states: [OPEN, CLOSED], first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          createdAt
          closedAt
          author { login }
          comments(first: 1) {
            nodes { createdAt author { login } }
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""
