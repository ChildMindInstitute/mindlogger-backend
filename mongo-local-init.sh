#!/bin/bash
set -e;
# the mongo image only creates a root user in the admin database and not in the initdb_database
# so this script will grant a root role in the initdb_database aswell

# a default non-root role
# MONGO_NON_ROOT_ROLE="${MONGO_NON_ROOT_ROLE:-readWrite}"

if [ -n "${MONGO_INITDB_ROOT_USERNAME:-}" ] && [ -n "${MONGO_INITDB_ROOT_PASSWORD:-}" ]; then
	"${mongo[@]}" "$MONGO_INITDB_DATABASE" <<-EOJS
        db.createUser({
            user: $(_js_escape "$MONGO_INITDB_ROOT_USERNAME"),
            pwd: $(_js_escape "$MONGO_INITDB_ROOT_PASSWORD"),
            roles: [ 
                { role: $(_js_escape "root"), db: $(_js_escape "admin") }, 
                { role: "dbOwner", db: $(_js_escape "$MONGO_INITDB_DATABASE") } 
                ]
            })
	EOJS
    		# db.createUser({
			# user: $(_js_escape "$MONGO_INITDB_ROOT_USERNAME"),
			# pwd: $(_js_escape "$MONGO_INITDB_ROOT_PASSWORD"),
			# roles: [ { role: "dbOwner", db: $(_js_escape "$MONGO_INITDB_DATABASE") }, ]
			# })
        #             db.grantRolesToUser(
        #     $(_js_escape "$MONGO_INITDB_ROOT_USERNAME"),
        #     [
        #     { role: "root", db: $(_js_escape "$MONGO_INITDB_DATABASE") }
        #     ]
        # )

        #     db.createUser({
		# 	user: $(_js_escape "$MONGO_INITDB_ROOT_USERNAME"),
		# 	pwd: $(_js_escape "$MONGO_INITDB_ROOT_PASSWORD"),
		# 	roles: [ { role: $(_js_escape "root"), db: $(_js_escape "admin") }, ]
		# 	})
# else
# 	# print warning or kill temporary mongo and exit non-zero
fi