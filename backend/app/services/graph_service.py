import logging
from typing import Any
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try importing neo4j
try:
    from neo4j import GraphDatabase, Driver
    NEO4J_AVAILABLE = True
except ImportError:
    GraphDatabase = None
    Driver = Any
    NEO4J_AVAILABLE = False


class Neo4jGraphService:
    def __init__(self):
        self._driver: Driver | None = None
        self._connected: bool = False

    def get_driver(self) -> Driver | None:
        if not NEO4J_AVAILABLE:
            return None
        if self._driver is not None:
            return self._driver

        auth = (settings.neo4j_user, settings.neo4j_password)
        candidate_uris = [settings.neo4j_uri]
        if "://neo4j:" in settings.neo4j_uri:
            candidate_uris.append(settings.neo4j_uri.replace("://neo4j:", "://localhost:"))
        elif "://localhost:" in settings.neo4j_uri:
            candidate_uris.append(settings.neo4j_uri.replace("://localhost:", "://neo4j:"))

        last_err = None
        for uri in candidate_uris:
            try:
                driver = GraphDatabase.driver(uri, auth=auth)
                driver.verify_connectivity()
                self._driver = driver
                self._connected = True
                logger.info("Successfully connected to Neo4j at %s", uri)
                return self._driver
            except Exception as e:
                last_err = e
                continue

        logger.warning("Neo4j is currently unreachable (%s). Graph queries will fallback gracefully.", str(last_err))
        self._connected = False
        return None

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connected = False

    def check_health(self) -> dict[str, Any]:
        driver = self.get_driver()
        if not driver:
            return {
                "status": "unavailable",
                "uri": settings.neo4j_uri,
                "message": "Neo4j is not connected or driver failed to initialize.",
                "nodes_count": 0,
                "relationships_count": 0,
            }

        try:
            with driver.session() as session:
                node_res = session.run("MATCH (n) RETURN count(n) AS cnt")
                node_count = node_res.single()["cnt"]

                rel_res = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
                rel_count = rel_res.single()["cnt"]

                return {
                    "status": "connected",
                    "uri": settings.neo4j_uri,
                    "nodes_count": node_count,
                    "relationships_count": rel_count,
                }
        except Exception as e:
            return {
                "status": "error",
                "uri": settings.neo4j_uri,
                "message": str(e),
                "nodes_count": 0,
                "relationships_count": 0,
            }

    def init_schema(self) -> bool:
        """Create uniqueness constraints on IDs."""
        driver = self.get_driver()
        if not driver:
            return False

        queries = [
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT community_id_unique IF NOT EXISTS FOR (c:Community) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT place_id_unique IF NOT EXISTS FOR (p:Place) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT interest_name_unique IF NOT EXISTS FOR (i:Interest) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT goal_name_unique IF NOT EXISTS FOR (g:Goal) REQUIRE g.name IS UNIQUE",
        ]

        try:
            with driver.session() as session:
                for q in queries:
                    session.run(q)
            logger.info("Neo4j schema constraints successfully applied.")
            return True
        except Exception as e:
            logger.error("Failed to apply Neo4j schema: %s", str(e))
            return False

    def sync_all_from_postgres(self, db: Session) -> dict[str, Any]:
        """
        Synchronizes all primary entities from PostgreSQL into the Neo4j Knowledge Graph:
        - User and Profile nodes with HAS_INTEREST, HAS_SKILL, HAS_GOAL
        - Community nodes and MEMBER_OF relationships
        - Event nodes and ATTENDS relationships
        - Place nodes
        - User-to-User CONNECTED_TO relationships
        """
        driver = self.get_driver()
        if not driver:
            return {"status": "skipped", "reason": "Neo4j driver unavailable"}

        self.init_schema()

        from app.models.user import User, Profile
        from app.models.community import Community, CommunityMembership
        from app.models.event import Event, EventRegistration
        from app.models.place import Place
        from app.models.connection import UserConnection

        users = db.query(User).all()
        communities = db.query(Community).all()
        memberships = db.query(CommunityMembership).all()
        events = db.query(Event).all()
        registrations = db.query(EventRegistration).all()
        places = db.query(Place).all()
        connections = db.query(UserConnection).filter(UserConnection.status == "accepted").all()

        synced_counts = {
            "users": 0,
            "communities": 0,
            "events": 0,
            "places": 0,
            "memberships": 0,
            "registrations": 0,
            "connections": 0,
            "interests": 0,
            "skills": 0,
            "goals": 0,
        }

        with driver.session() as session:
            # 1. Sync Users & Profiles
            for u in users:
                prof = u.profile
                interests = [i.strip().lower() for i in (prof.interests.split(",") if prof and prof.interests else []) if i.strip()]
                skills = [s.strip().lower() for s in (prof.skills.split(",") if prof and prof.skills else []) if s.strip()]
                goals = [g.strip().lower() for g in (prof.goals.split(",") if prof and prof.goals else []) if g.strip()]

                session.run(
                    """
                    MERGE (u:User {id: $id})
                    SET u.name = $name,
                        u.email = $email,
                        u.location = $location
                    """,
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    location=prof.location if prof else "",
                )
                synced_counts["users"] += 1

                for item in interests:
                    session.run(
                        """
                        MERGE (i:Interest {name: $name})
                        WITH i
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_INTEREST]->(i)
                        """,
                        name=item,
                        uid=u.id,
                    )
                    synced_counts["interests"] += 1

                for item in skills:
                    session.run(
                        """
                        MERGE (s:Skill {name: $name})
                        WITH s
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_SKILL]->(s)
                        """,
                        name=item,
                        uid=u.id,
                    )
                    synced_counts["skills"] += 1

                for item in goals:
                    session.run(
                        """
                        MERGE (g:Goal {name: $name})
                        WITH g
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_GOAL]->(g)
                        """,
                        name=item,
                        uid=u.id,
                    )
                    synced_counts["goals"] += 1

            # 2. Sync Communities
            for c in communities:
                tags = [t.strip().lower() for t in (c.tags.split(",") if c.tags else []) if t.strip()]
                session.run(
                    """
                    MERGE (c:Community {id: $id})
                    SET c.name = $name,
                        c.category = $category,
                        c.location = $location
                    """,
                    id=c.id,
                    name=c.name,
                    category=c.category,
                    location=c.location,
                )
                synced_counts["communities"] += 1

                for t in tags:
                    session.run(
                        """
                        MERGE (i:Interest {name: $tag})
                        WITH i
                        MATCH (c:Community {id: $cid})
                        MERGE (c)-[:HAS_TAG]->(i)
                        """,
                        tag=t,
                        cid=c.id,
                    )

            # 3. Sync Community Memberships
            for m in memberships:
                session.run(
                    """
                    MATCH (u:User {id: $uid})
                    MATCH (c:Community {id: $cid})
                    MERGE (u)-[r:MEMBER_OF]->(c)
                    SET r.role = $role
                    """,
                    uid=m.user_id,
                    cid=m.community_id,
                    role=m.role,
                )
                synced_counts["memberships"] += 1

            # 4. Sync Events
            for e in events:
                session.run(
                    """
                    MERGE (ev:Event {id: $id})
                    SET ev.title = $title,
                        ev.category = $category,
                        ev.location = $location
                    """,
                    id=e.id,
                    title=e.title,
                    category=e.category,
                    location=e.location,
                )
                synced_counts["events"] += 1

                if e.community_id:
                    session.run(
                        """
                        MATCH (ev:Event {id: $eid})
                        MATCH (c:Community {id: $cid})
                        MERGE (c)-[:HOSTS]->(ev)
                        """,
                        eid=e.id,
                        cid=e.community_id,
                    )

            # 5. Sync Event Registrations
            for r in registrations:
                session.run(
                    """
                    MATCH (u:User {id: $uid})
                    MATCH (ev:Event {id: $eid})
                    MERGE (u)-[att:ATTENDS]->(ev)
                    SET att.status = $status
                    """,
                    uid=r.user_id,
                    eid=r.event_id,
                    status=r.status,
                )
                synced_counts["registrations"] += 1

            # 6. Sync Places
            for p in places:
                session.run(
                    """
                    MERGE (pl:Place {id: $id})
                    SET pl.name = $name,
                        pl.category = $category,
                        pl.address = $address,
                        pl.city = $city
                    """,
                    id=p.id,
                    name=p.name,
                    category=p.category,
                    address=p.address,
                    city=p.city,
                )
                synced_counts["places"] += 1

            # 7. Sync Connections
            for conn in connections:
                session.run(
                    """
                    MATCH (u1:User {id: $uid1})
                    MATCH (u2:User {id: $uid2})
                    MERGE (u1)-[:CONNECTED_TO]-(u2)
                    """,
                    uid1=conn.sender_id,
                    uid2=conn.receiver_id,
                )
                synced_counts["connections"] += 1

        logger.info("Neo4j full sync completed: %s", synced_counts)
        return {"status": "success", "synced": synced_counts}

    def get_community_graph_details(
        self, user_id: int, community_id: int, community_name: str = "Community"
    ) -> tuple[float, str | None, dict[str, Any]]:
        """
        Computes graph overlap affinity between a user and a community and returns
        the normalized score, human-readable graph connection path, and topology metrics.
        Never leaks private information (uses public names / aggregate counts).
        """
        driver = self.get_driver()
        if not driver:
            return 0.0, None, {}

        try:
            with driver.session() as session:
                query = """
                MATCH (u:User {id: $uid})
                MATCH (c:Community {id: $cid})
                OPTIONAL MATCH (u)-[:HAS_INTEREST]->(i:Interest)<-[:HAS_TAG]-(c)
                WITH u, c, collect(DISTINCT i.name)[0..3] AS shared_tags_list, count(DISTINCT i) AS shared_tags
                OPTIONAL MATCH (u)-[:CONNECTED_TO]-(friend:User)-[:MEMBER_OF]->(c)
                RETURN shared_tags_list, shared_tags, collect(DISTINCT friend.name)[0..2] AS friend_names, count(DISTINCT friend) AS friend_members
                """
                res = session.run(query, uid=user_id, cid=community_id).single()
                if not res:
                    return 0.0, None, {}

                shared_tags = res["shared_tags"] or 0
                shared_tags_list = [str(x) for x in (res["shared_tags_list"] or []) if x]
                friend_members = res["friend_members"] or 0
                friend_names = [str(x) for x in (res["friend_names"] or []) if x]

                raw_score = min(1.0, (shared_tags * 0.2) + (friend_members * 0.3))
                details = {
                    "shared_tags": shared_tags,
                    "shared_tags_list": shared_tags_list,
                    "friend_members": friend_members,
                    "friend_names": friend_names,
                }

                graph_path = None
                if friend_members > 0:
                    friend_display = friend_names[0] if friend_names else "connection"
                    if friend_members > 1:
                        graph_path = f"You → ({friend_display} + {friend_members - 1} network connection{'s' if friend_members - 1 > 1 else ''}) → (member of) → {community_name}"
                    else:
                        graph_path = f"You → (connection: {friend_display}) → (member of) → {community_name}"
                elif shared_tags > 0:
                    tag_str = ", ".join(shared_tags_list[:2]) if shared_tags_list else "shared tag"
                    graph_path = f"You → (shared interest: {tag_str}) → {community_name}"

                return raw_score, graph_path, details
        except Exception as e:
            logger.debug(f"Community graph details lookup error: {e}")
            return 0.0, None, {}

    def get_community_graph_score(self, user_id: int, community_id: int) -> float:
        score, _, _ = self.get_community_graph_details(user_id, community_id)
        return score

    def get_peer_graph_details(
        self, user_id: int, target_user_id: int, target_name: str = "Peer"
    ) -> tuple[float, str | None, dict[str, Any]]:
        """
        Computes graph affinity between two peers and returns the normalized score,
        path, and topology metrics with zero private leakage.
        """
        if user_id == target_user_id:
            return 0.0, None, {}

        driver = self.get_driver()
        if not driver:
            return 0.0, None, {}

        try:
            with driver.session() as session:
                query = """
                MATCH (u1:User {id: $uid1})
                MATCH (u2:User {id: $uid2})
                OPTIONAL MATCH (u1)-[:HAS_INTEREST]->(i:Interest)<-[:HAS_INTEREST]-(u2)
                WITH u1, u2, collect(DISTINCT i.name)[0..3] AS shared_interests_list, count(DISTINCT i) AS shared_interests
                OPTIONAL MATCH (u1)-[:MEMBER_OF]->(c:Community)<-[:MEMBER_OF]-(u2)
                WITH u1, u2, shared_interests_list, shared_interests, collect(DISTINCT c.name)[0..2] AS shared_comms_list, count(DISTINCT c) AS shared_communities
                OPTIONAL MATCH (u1)-[:CONNECTED_TO]-(mutual:User)-[:CONNECTED_TO]-(u2)
                RETURN shared_interests_list, shared_interests, shared_comms_list, shared_communities, collect(DISTINCT mutual.name)[0..2] AS mutual_names, count(DISTINCT mutual) AS mutual_friends
                """
                res = session.run(query, uid1=user_id, uid2=target_user_id).single()
                if not res:
                    return 0.0, None, {}

                shared_interests = res["shared_interests"] or 0
                shared_interests_list = [str(x) for x in (res["shared_interests_list"] or []) if x]
                shared_communities = res["shared_communities"] or 0
                shared_comms_list = [str(x) for x in (res["shared_comms_list"] or []) if x]
                mutual_friends = res["mutual_friends"] or 0
                mutual_names = [str(x) for x in (res["mutual_names"] or []) if x]

                raw_score = min(1.0, (shared_interests * 0.2) + (shared_communities * 0.3) + (mutual_friends * 0.3))
                details = {
                    "shared_interests": shared_interests,
                    "shared_interests_list": shared_interests_list,
                    "shared_communities": shared_communities,
                    "shared_comms_list": shared_comms_list,
                    "mutual_friends": mutual_friends,
                    "mutual_names": mutual_names,
                }

                graph_path = None
                if mutual_friends > 0:
                    m_name = mutual_names[0] if mutual_names else "mutual connection"
                    graph_path = f"You → (connection: {m_name}) → (connected) → {target_name}"
                elif shared_communities > 0:
                    c_name = shared_comms_list[0] if shared_comms_list else "shared community"
                    graph_path = f"You → (member of: {c_name}) ← (member) ← {target_name}"
                elif shared_interests > 0:
                    i_name = ", ".join(shared_interests_list[:2]) if shared_interests_list else "shared interest"
                    graph_path = f"You → (interest: {i_name}) ← (interest) ← {target_name}"

                return raw_score, graph_path, details
        except Exception as e:
            logger.debug(f"Peer graph details lookup error: {e}")
            return 0.0, None, {}

    def get_peer_graph_score(self, user_id: int, target_user_id: int) -> float:
        score, _, _ = self.get_peer_graph_details(user_id, target_user_id)
        return score

    def get_event_graph_details(
        self, user_id: int, event_id: int, event_title: str = "Event"
    ) -> tuple[float, str | None, dict[str, Any]]:
        """
        Computes graph affinity for an event and returns score, path, and attendees summary.
        """
        driver = self.get_driver()
        if not driver:
            return 0.0, None, {}

        try:
            with driver.session() as session:
                query = """
                MATCH (u:User {id: $uid})
                MATCH (ev:Event {id: $eid})
                OPTIONAL MATCH (u)-[:MEMBER_OF]->(c:Community)-[:HOSTS]->(ev)
                WITH u, ev, collect(DISTINCT c.name)[0..1] AS host_comm_names, count(DISTINCT c) AS host_member
                OPTIONAL MATCH (u)-[:CONNECTED_TO]-(friend:User)-[:ATTENDS]->(ev)
                RETURN host_comm_names, host_member, collect(DISTINCT friend.name)[0..2] AS friend_names, count(DISTINCT friend) AS friend_attendees
                """
                res = session.run(query, uid=user_id, eid=event_id).single()
                if not res:
                    return 0.0, None, {}

                host_member = res["host_member"] or 0
                host_comm_names = [str(x) for x in (res["host_comm_names"] or []) if x]
                friend_attendees = res["friend_attendees"] or 0
                friend_names = [str(x) for x in (res["friend_names"] or []) if x]

                raw_score = min(1.0, (0.5 if host_member > 0 else 0.0) + (friend_attendees * 0.25))
                details = {
                    "host_member": host_member,
                    "host_comm_names": host_comm_names,
                    "friend_attendees": friend_attendees,
                    "friend_names": friend_names,
                }

                graph_path = None
                if friend_attendees > 0:
                    f_name = friend_names[0] if friend_names else "connection"
                    graph_path = f"You → (connection: {f_name}) → (attending) → {event_title}"
                elif host_member > 0:
                    c_name = host_comm_names[0] if host_comm_names else "host community"
                    graph_path = f"You → (member of: {c_name}) → (hosts) → {event_title}"

                return raw_score, graph_path, details
        except Exception as e:
            logger.debug(f"Event graph details lookup error: {e}")
            return 0.0, None, {}

    def get_event_graph_score(self, user_id: int, event_id: int) -> float:
        score, _, _ = self.get_event_graph_details(user_id, event_id)
        return score

    def sync_user_profile(
        self,
        user_id: int,
        name: str,
        email: str,
        location: str = "",
        interests: list[str] | None = None,
        skills: list[str] | None = None,
        goals: list[str] | None = None,
    ) -> bool:
        """Real-time update of a single user node and their interest/skill/goal edges."""
        driver = self.get_driver()
        if not driver:
            return False
        try:
            interests = [i.strip().lower() for i in (interests or []) if i.strip()]
            skills = [s.strip().lower() for s in (skills or []) if s.strip()]
            goals = [g.strip().lower() for g in (goals or []) if g.strip()]

            with driver.session() as session:
                session.run(
                    """
                    MERGE (u:User {id: $id})
                    SET u.name = $name,
                        u.email = $email,
                        u.location = $location
                    """,
                    id=user_id,
                    name=name,
                    email=email,
                    location=location,
                )
                # Re-sync interests
                session.run(
                    "MATCH (u:User {id: $uid})-[r:HAS_INTEREST]->() DELETE r",
                    uid=user_id,
                )
                for item in interests:
                    session.run(
                        """
                        MERGE (i:Interest {name: $name})
                        WITH i
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_INTEREST]->(i)
                        """,
                        name=item,
                        uid=user_id,
                    )

                # Re-sync skills
                session.run(
                    "MATCH (u:User {id: $uid})-[r:HAS_SKILL]->() DELETE r",
                    uid=user_id,
                )
                for item in skills:
                    session.run(
                        """
                        MERGE (s:Skill {name: $name})
                        WITH s
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_SKILL]->(s)
                        """,
                        name=item,
                        uid=user_id,
                    )

                # Re-sync goals
                session.run(
                    "MATCH (u:User {id: $uid})-[r:HAS_GOAL]->() DELETE r",
                    uid=user_id,
                )
                for item in goals:
                    session.run(
                        """
                        MERGE (g:Goal {name: $name})
                        WITH g
                        MATCH (u:User {id: $uid})
                        MERGE (u)-[:HAS_GOAL]->(g)
                        """,
                        name=item,
                        uid=user_id,
                    )
            return True
        except Exception as e:
            logger.warning("Failed to sync user %d to Neo4j: %s", user_id, str(e))
            return False

    def sync_connection(self, sender_id: int, receiver_id: int, connected: bool) -> bool:
        """Real-time update of user connection edge."""
        driver = self.get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                if connected:
                    session.run(
                        """
                        MATCH (u1:User {id: $uid1})
                        MATCH (u2:User {id: $uid2})
                        MERGE (u1)-[:CONNECTED_TO]-(u2)
                        """,
                        uid1=sender_id,
                        uid2=receiver_id,
                    )
                else:
                    session.run(
                        """
                        MATCH (u1:User {id: $uid1})-[r:CONNECTED_TO]-(u2:User {id: $uid2})
                        DELETE r
                        """,
                        uid1=sender_id,
                        uid2=receiver_id,
                    )
            return True
        except Exception as e:
            logger.warning("Failed to sync connection in Neo4j: %s", str(e))
            return False

    def sync_community_membership(self, user_id: int, community_id: int, joined: bool, role: str = "member") -> bool:
        """Real-time update of community membership edge."""
        driver = self.get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                if joined:
                    session.run(
                        """
                        MATCH (u:User {id: $uid})
                        MATCH (c:Community {id: $cid})
                        MERGE (u)-[r:MEMBER_OF]->(c)
                        SET r.role = $role
                        """,
                        uid=user_id,
                        cid=community_id,
                        role=role,
                    )
                else:
                    session.run(
                        """
                        MATCH (u:User {id: $uid})-[r:MEMBER_OF]->(c:Community {id: $cid})
                        DELETE r
                        """,
                        uid=user_id,
                        cid=community_id,
                    )
            return True
        except Exception as e:
            logger.warning("Failed to sync community membership in Neo4j: %s", str(e))
            return False

    def sync_event_registration(self, user_id: int, event_id: int, registered: bool, status: str = "confirmed") -> bool:
        """Real-time update of event attendance edge."""
        driver = self.get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                if registered:
                    session.run(
                        """
                        MATCH (u:User {id: $uid})
                        MATCH (ev:Event {id: $eid})
                        MERGE (u)-[att:ATTENDS]->(ev)
                        SET att.status = $status
                        """,
                        uid=user_id,
                        eid=event_id,
                        status=status,
                    )
                else:
                    session.run(
                        """
                        MATCH (u:User {id: $uid})-[att:ATTENDS]->(ev:Event {id: $eid})
                        DELETE att
                        """,
                        uid=user_id,
                        eid=event_id,
                    )
            return True
        except Exception as e:
            logger.warning("Failed to sync event registration in Neo4j: %s", str(e))
            return False

    def delete_user_node(self, user_id: int) -> bool:
        """Permanently deletes a User node and all incident relationships from Neo4j."""
        driver = self.get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                session.run("MATCH (u:User {id: $user_id}) DETACH DELETE u", user_id=user_id)
            return True
        except Exception as e:
            logger.warning("Failed to delete user node in Neo4j: %s", str(e))
            return False

    def get_graph_stats(self) -> dict[str, Any]:
        """Returns graph node and edge counts by label and type."""
        driver = self.get_driver()
        if not driver:
            return {"status": "unavailable"}

        try:
            with driver.session() as session:
                labels_res = session.run("CALL db.labels() YIELD label RETURN label")
                labels = [r["label"] for r in labels_res]

                node_counts = {}
                for l in labels:
                    c_res = session.run(f"MATCH (n:`{l}`) RETURN count(n) AS cnt")
                    node_counts[l] = c_res.single()["cnt"]

                types_res = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                rel_types = [r["relationshipType"] for r in types_res]

                rel_counts = {}
                for t in rel_types:
                    c_res = session.run(f"MATCH ()-[r:`{t}`]->() RETURN count(r) AS cnt")
                    rel_counts[t] = c_res.single()["cnt"]

                return {
                    "status": "connected",
                    "node_counts": node_counts,
                    "relationship_counts": rel_counts,
                    "total_nodes": sum(node_counts.values()),
                    "total_relationships": sum(rel_counts.values()),
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}


graph_service = Neo4jGraphService()
