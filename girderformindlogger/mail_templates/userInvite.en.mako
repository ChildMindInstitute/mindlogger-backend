## -*- coding: utf-8 -*-
<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>
        Hello ${userName}!
    </p>

    <p>
        You were invited by ${coordinatorName} to be a ${role} of "${appletName}" applet on MindLogger. 
    <br>
        Below are users that have access to your data
    </p>

    <p>
        - Users who can see your data for this applet:
        ${reviewers}
    </p>

    <p>
        - Users who can change this applet's settings, including who can access your data:
        ${managers}
    </p>

    <p>
        - Users who can change this applet's settings, but who cannot change who can see your data:
        ${coordinators}
    </p>

    <p style="text-align: center;">
        <a
            href="${url}/accept"
            style="padding: 0.4rem 1rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(88, 217, 65); border-color: rgb(88, 217, 65);"
        >
            Accept
        </a> 
    </p>

    <p style="text-align: center;">
        <a
            href="${url}/decline"
            style="padding: 0.4rem 1rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(224, 52, 56); border-color: rgb(224, 52, 56);"
        >
            Decline
        </a>
    </p>
</div>

<%include file="_footer.mako"/>
